#! /usr/bin/env python3
import sys
import gzip
# import zstandard
import json
import datetime
from typing import Tuple
from collections import Counter, defaultdict

# -------------------------------------------------------------

s_cluster = "model_k8s_cluster:"
s_node = "model_k8s_node"
s_pod = "model_k8s_pod"
s_container = "model_container"
s_conn = "model_connection"
s_proc = "model_process"

report_schemas = [s_cluster, s_node, s_pod, s_container, s_conn, s_proc]
tt_registry = {}


def smart_open(fn, mode):
    if fn is None:
        if 'a' in mode or 'w' in mode:
            return sys.stdout
        else:
            return sys.stdin
    if fn.endswith('.gz'):
        return gzip.open(fn, mode)
    # elif fn.endswith('.zst') or fn.endswith('.zstd'):
    #     return zstandard.open(fn, mode)
    else:
        return open(fn, mode)


def datacollector(args):
    data = []
    if hasattr(args, "input") and args.input is not None:
        for filename in args.input.split(","):
            with smart_open(filename, "rt") as f:
                data.extend([json.loads(line) for line in f])
    else:
        raise NotImplementedError(
            "No support yet to pull this reports data on demand from api yet")
    return data


def make_index(rec_list: list, schemas: list[str]) -> Tuple[dict, dict]:
    index = dict()
    schema_index = defaultdict(dict)
    for rec in rec_list:
        for schema in schemas:
            if schema in rec["schema"]:
                index[rec["id"]] = rec
                schema_index[schema][rec["id"]] = rec
    return index, schema_index


def tt_get_puid(rec):
    puid = rec["puids"][0]
    return puid


def tt_record(rec):
    global tt_registry
    puid = tt_get_puid(rec)
    payload = rec.get("payload")
    if puid not in tt_registry:
        tt_registry[puid] = TopTalker(puid)
    tt_registry[puid].add(rec["time"], payload)


def top_talkers():
    global tt_registry
    rv = list(tt_registry.values())
    rv.sort(key=lambda x: x.count, reverse=True)
    return rv


class TopTalker:
    def __init__(self, puid):
        self.start = 0
        self.end = 0
        self.count = 0
        self.puid = puid
        self.payloads = set()

    def add(self, t, payload):
        if self.start == 0:
            self.start = self.end = t
            self.count = 1
        else:
            if t < self.start:
                self.start = t
            if t > self.end:
                self.end = t
            self.count += 1
        for x in payload.split():
            self.payloads.add(x)

    def to_dict(self, index: dict):
        cluster = None
        node = None
        namespace = None
        image = None
        pod_name = None
        container = None
        proc_name = None
        start = ""
        end = ""
        req = None
        rps = None
        proc = index.get(self.puid)
        if proc is None:
            return ""
        proc_name = proc['name']
        node = proc['muid']
        cont = index.get(proc.get('container_uid'), {})
        if not cont:
            namespace = proc.get('cgroup')
        else:
            pod = index.get(cont.get('pod_uid'), {})
            image = cont.get('image')
            namespace = cont.get('pod_namespace')
            cluster = cont.get('clustername')
            container = cont.get('container_id')
            pod_name = cont.get('pod_name')

        start = datetime.datetime.fromtimestamp(self.start).isoformat()
        end = datetime.datetime.fromtimestamp(self.end).isoformat()
        dt = self.end - self.start
        req = self.count
        payloads = list(self.payloads)
        if dt == 0:
            rps = "0.0"
        else:
            rps = "%1.3f" % (self.count/dt)
        return {
            "cluster": cluster,
            "node": node,
            "namespace": namespace,
            "image": image,
            "pod": pod_name,
            "container": container,
            "proc_name": proc_name,
            "start": start,
            "end": end,
            "req": req,
            "rps": rps,
            "payloads": payloads
        }


def dataprocessor(data: list, format: str, mock: dict = {}) -> dict:

    context = mock
    index, schema_index = make_index(rec_list=data, schemas=report_schemas)

    # Cluster name and id
    cluster = list(schema_index[s_cluster].values())[0]
    context["cluster"] = {
        "name": cluster["name"],
        "cluid": cluster["id"],
        "node_count": len(schema_index.get(s_node, []))
    }

    # Get set of machines related to cluster
    cluster_machines = {node.get("muid")
                        for node in schema_index[s_node].values()
                        if node.get("muid") is not None}

    domain_count = Counter()

    for rec in data:
        if (
            rec["schema"] == "model_connection::1.1.0"
            and rec["muid"] in cluster_machines
            and rec["proto"] == "UDP"
            and rec["remote_port"] == 53
            and rec.get("payload") is not None
        ):
            tt_record(rec)
        elif (
            rec["schema"] == "dns_capture_request:bat:1.0.0"
            and rec["muid"] in cluster_machines
        ):
            name = rec["name"].strip(".")
            domain_count[name] += len(rec["src_ports"])

    context["top_talkers"] = [tt.to_dict(index) for tt in top_talkers()]
    context["top_domains"] = domain_count.most_common()
    return context
