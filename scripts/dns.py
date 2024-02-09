#! /usr/bin/env python3
import sys
import gzip
import json
import argparse
import datetime

from collections import Counter

# -------------------------------------------------------------

tt_registry = {}


def tt_make_key(rec):
    puid = rec["puids"][0]
    return puid


def tt_record(rec):
    global tt_registry
    key = tt_make_key(rec)
    payload = rec.get("payload")
    if key not in tt_registry:
        puid = rec["puids"][0]
        tt_registry[key] = TopTalker(puid)
    tt_registry[key].add(rec["time"], payload)


def top_talkers():
    global tt_registry
    rv = list(tt_registry.values())
    rv.sort(key=lambda x: x.count, reverse=True)
    return rv


class TopTalker:
    def __init__(self, puid):
        self.start = None
        self.end = None
        self.count = None
        self.puid = puid
        self.payloads = set()

    def add(self, t, payload):
        if self.start is None:
            self.start = self.end = t
            self.count = 1
        else:
            self.end = t
            self.count += 1
        for x in payload.split():
            self.payloads.add(x)

    @property
    def key(self):
        return self.puid

    @classmethod
    def header(self):
        return "cluster,node,namespace,image,pod,container,process,start,end,req,req/sec,domains"

    def body(self):
        cluster = None
        node = None
        namespace = None
        image = None
        pod_name = None
        container = None
        proc_name = None
        start = None
        end = None
        req = None
        rps = None
        proc = IDO.get(self.puid)
        if proc is None:
            return ""
        proc_name = proc['name']
        node = proc['muid']
        cont = IDO.get(proc.get('container_uid'), {})
        if not cont:
            namespace = proc.get('cgroup')
        else:
            pod = IDO.get(cont.get('pod_uid'), {})
            image = cont.get('image')
            namespace = cont.get('pod_namespace')
            cluster = cont.get('clustername')
            container = cont.get('container_id')
            pod_name = cont.get('pod_name')

        start = datetime.datetime.fromtimestamp(self.start).isoformat()
        end = datetime.datetime.fromtimestamp(self.end).isoformat()
        dt = self.end-self.start
        req = self.count
        payloads = ' '.join(list(self.payloads))
        if dt == 0:
            rps = "0.0"
        else:
            rps = "%1.3f" % (self.count/dt)
        return f"{cluster},{node},{namespace},{image},{pod_name},{container},{proc_name},{start},{end},{req},{rps},{payloads}"


IDO = {}  # id -> model_process, model_k8s_pod, model_container


# -------------------------------------------------------------
def _parse_cmd_line():
    parser = argparse.ArgumentParser(
        description="Combine multiple ndjson files by time",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-i", "--infile")
    parser.add_argument("-o", "--outfile")
    args = parser.parse_args()
    return args


options = _parse_cmd_line()


def smart_open(fn, mode):
    if fn is None:
        if "r" in mode:
            return sys.stdin
        return sys.stdout
    if fn.endswith(".gz"):
        return gzip.open(fn, mode)
    return open(fn, mode)


infile = smart_open(options.infile, "rt")
outfile = smart_open(options.outfile, "wt")

domain_count = Counter()

for line in infile:
    rec = json.loads(line)
    if (
        rec["schema"] == "model_connection::1.1.0"
        and rec["proto"] == "UDP"
        and rec["remote_port"] == 53
        and rec.get("payload") is not None
    ):
        tt_record(rec)
    elif (
        rec["schema"] == "model_process::1.2.0"
        or rec["schema"] == "model_container::1.0.0"
        or rec["schema"] == "model_k8s_node::1.0.0"
        or rec["schema"] == "model_k8s_pod::1.0.0"
    ):
        IDO[rec["id"]] = rec
    elif rec["schema"] == "dns_capture_request:bat:1.0.0":
        name = rec["name"].strip(".")
        domain_count[name] += len(rec["src_ports"])

print(TopTalker.header())
for tt in top_talkers():
    body = tt.body()
    if body:
        print(body)

print("")
print("domain,count")
for key, value in domain_count.most_common():
    print(f"{key},{value}")
