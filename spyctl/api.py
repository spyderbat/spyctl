import json
import sys
import time
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import tqdm
import zulu

import spyctl.cli as cli
import spyctl.resources.fingerprints as spyctl_fprints
import spyctl.spyctl_lib as lib

# Get policy parameters
GET_POL_TYPE = "type"
GET_POL_HAS_TAGS = "has_tags"
GET_POL_NAME_CONTAINS = "name_contains"
GET_POL_POLICY_CONTAINS = "policy_contains"
GET_POL_SELECTOR_CONTAINS = "selector_contains"
GET_POL_UID_EQUALS = "uid_equals"


# https://requests.readthedocs.io/en/latest/user/advanced/#timeouts
# connection timeout, read timeout
TIMEOUT = (6.10, 300)
AUTO_HIDE_TIME = zulu.now().shift(days=-1)


def get(url, key, params=None):
    headers = {"Authorization": f"Bearer {key}"}
    r = requests.get(url, headers=headers, timeout=TIMEOUT, params=params)
    if r.status_code != 200:
        if "x-context-uid" in r.headers:
            context_uid = r.headers["x-context-uid"]
        else:
            context_uid = "No context uid found."
        cli.err_exit(
            f"{r.status_code}, {r.reason}\n\tContext UID: {context_uid}"
        )
    return r


def post(url, data, key):
    headers = {"Authorization": f"Bearer {key}"}
    r = requests.post(url, json=data, headers=headers, timeout=TIMEOUT)
    if r.status_code != 200:
        if "x-context-uid" in r.headers:
            context_uid = r.headers["x-context-uid"]
        else:
            context_uid = "No context uid found."
        cli.err_exit(
            f"{r.status_code}, {r.reason}\n\tContext UID: {context_uid}"
        )
    return r


def put(url, data, key):
    headers = {"Authorization": f"Bearer {key}"}
    r = requests.put(url, json=data, headers=headers, timeout=TIMEOUT)
    if r.status_code != 200:
        if "x-context-uid" in r.headers:
            context_uid = r.headers["x-context-uid"]
        else:
            context_uid = "No context uid found."
        cli.err_exit(
            f"{r.status_code}, {r.reason}\n\tContext UID: {context_uid}"
        )
    return r


def delete(url, key):
    headers = {"Authorization": f"Bearer {key}"}
    r = requests.delete(url, headers=headers, timeout=TIMEOUT)
    if r.status_code != 200:
        if "x-context-uid" in r.headers:
            context_uid = r.headers["x-context-uid"]
        else:
            context_uid = "No context uid found."
        cli.err_exit(
            f"{r.status_code}, {r.reason}\n\tContext UID: {context_uid}"
        )
    return r


def get_orgs(api_url, api_key) -> List[Tuple]:
    org_uids = []
    org_names = []
    url = f"{api_url}/api/v1/org/"
    orgs_json = get(url, api_key).json()
    for org in orgs_json:
        org_uids.append(org["uid"])
        org_names.append(org["name"])
    return (org_uids, org_names)


def get_machines(api_url, api_key, org_uid) -> List[Dict]:
    machines: Dict[str, Dict] = {}
    url = f"{api_url}/api/v1/org/{org_uid}/source/"
    source_json = get(url, api_key).json()
    for source in source_json:
        src_uid = source["uid"]
        if not src_uid.startswith("global"):
            machines[src_uid] = source
    # agents API call to find "description" (name used by the UI)
    url = f"{api_url}/api/v1/org/{org_uid}/agent/"
    agent_json = get(url, api_key).json()
    for agent in agent_json:
        src_uid = agent["runtime_details"]["src_uid"]
        description = agent["description"]
        if not agent["uid"].startswith("global"):
            source = machines.get(src_uid)
            if source is None:
                continue
            source.update(agent)
            machine = {}
            machine["uid"] = src_uid
            machine["name"] = description
            del source["uid"]
            del source["description"]
            del source["name"]
            machine.update(source)
            machines[src_uid] = machine
    # Auto-hide inactive machines
    rv = []
    for machine in machines.values():
        if (
            zulu.Zulu.parse(machine["last_data"]) >= AUTO_HIDE_TIME
            or zulu.Zulu.parse(machine["last_stored_chunk_end_time"])
            >= AUTO_HIDE_TIME
        ) and "runtime_details" in machine:
            rv.append(machine)
    return rv


def get_muids(api_url, api_key, org_uid) -> Tuple:
    last_datas = {}
    sources = {}
    # get all sources to get last data
    url = f"{api_url}/api/v1/org/{org_uid}/source/"
    source_json = get(url, api_key).json()
    for source in source_json:
        if not source["uid"].startswith("global"):
            muid = source["uid"]
            last_data = zulu.parse(source["last_data"])
            last_datas[muid] = last_data
    # get agents to get hostnames
    url = f"{api_url}/api/v1/org/{org_uid}/agent/"
    source_json = get(url, api_key).json()
    for source in source_json:
        if not source["uid"].startswith("global"):
            muid = source["runtime_details"]["src_uid"]
            hostname = source["description"]
            if muid in last_datas:
                sources[muid] = {
                    "name": hostname,
                    "last_data": last_datas[muid],
                }
    check_time = zulu.Zulu.fromtimestamp(time.time()).shift(days=-1)
    machines = []
    for muid, data in list(sources.items()):
        if data["last_data"] >= check_time:
            machines.append(
                {
                    "name": data["name"],
                    "uid": muid,
                    "machine_details": {"last_data": str(data["last_data"])},
                }
            )
    return machines


def get_clusters(api_url, api_key, org_uid):
    clusters = []
    url = f"{api_url}/api/v1/org/{org_uid}/cluster/"
    json = get(url, api_key).json()
    for cluster in json:
        if "/" not in cluster["uid"]:
            clusters.append(cluster)
    return clusters


def get_k8s_data(api_url, api_key, org_uid, clus_uid, schema_key, time):
    url = f"{api_url}/api/v1/org/{org_uid}/data/"
    url += f"?src={clus_uid}&st={time[0]}&et={time[1]}&dt=k8s"
    resp = get(url, api_key)
    for k8s_json in resp.iter_lines():
        data = json.loads(k8s_json)
        if schema_key in data["schema"]:
            yield data


def get_clust_namespaces(api_url, api_key, org_uid, clus_uid, time):
    ns = set()
    for data in get_k8s_data(
        api_url, api_key, org_uid, clus_uid, "cluster", time
    ):
        data_ns = data.get("namespaces", set())
        ns.update(data_ns)
    return (sorted(ns), clus_uid)


def get_namespaces(api_url, api_key, org_uid, clusters, time):
    namespaces = []
    pbar = tqdm.tqdm(total=len(clusters), leave=False, file=sys.stderr)
    threads = []
    uid_to_name_map = {}
    with ThreadPoolExecutor() as executor:
        for cluster in clusters:
            if "/" in cluster["uid"]:
                continue
            uid_to_name_map[cluster["uid"]] = cluster["name"]
            threads.append(
                executor.submit(
                    get_clust_namespaces,
                    api_url,
                    api_key,
                    org_uid,
                    cluster["uid"],
                    time,
                )
            )
        for task in as_completed(threads):
            pbar.update(1)
            ns_list, uid = task.result()
            cluster_name = uid_to_name_map[uid]
            namespaces.append(
                {
                    "cluster_name": cluster_name,
                    "cluster_uid": uid,
                    "namespaces": ns_list,
                }
            )
    pbar.close()
    return namespaces


def get_nodes(api_url, api_key, org_uid, clusters, time) -> List[Dict]:
    nodes = []
    pbar = tqdm.tqdm(total=len(clusters), leave=False, file=sys.stderr)
    threads = []
    with ThreadPoolExecutor() as executor:
        for cluster in clusters:
            threads.append(
                executor.submit(
                    get_clust_nodes,
                    api_url,
                    api_key,
                    org_uid,
                    cluster["uid"],
                    time,
                )
            )
        for task in as_completed(threads):
            pbar.update(1)
            nodes.extend(task.result())
    pbar.close()
    return nodes


def get_clust_nodes(api_url, api_key, org_uid, clus_uid, time):
    nodes = {}
    for data in get_k8s_data(
        api_url, api_key, org_uid, clus_uid, "node", time
    ):
        node_id = data["id"]
        if node_id not in nodes:
            nodes[node_id] = data
        elif nodes[node_id]["time"] < data["time"]:
            nodes[node_id] = data
    return list(nodes.values())


def get_pods(api_url, api_key, org_uid, clusters, time) -> List[Dict]:
    pods = []
    pbar = tqdm.tqdm(total=len(clusters), leave=False, file=sys.stderr)
    threads = []
    with ThreadPoolExecutor() as executor:
        for cluster in clusters:
            threads.append(
                executor.submit(
                    get_clust_pods,
                    api_url,
                    api_key,
                    org_uid,
                    cluster["uid"],
                    time,
                )
            )
        for task in as_completed(threads):
            pbar.update(1)
            pods.extend(
                filter(
                    lambda rec: lib.KIND_FIELD in rec
                    and rec[lib.KIND_FIELD] == "Pod",
                    task.result(),
                )
            )
    pbar.close()
    return pods


def get_clust_pods(api_url, api_key, org_uid, clus_uid, time):
    pods = {}
    for data in get_k8s_data(api_url, api_key, org_uid, clus_uid, "pod", time):
        pod_id = data["id"]
        if pod_id not in pods:
            pods[pod_id] = data
        elif pods[pod_id]["time"] < data["time"]:
            pods[pod_id] = data
    return list(pods.values())


def get_fingerprints(api_url, api_key, org_uid, muids, time):
    fingerprints = []
    pbar = tqdm.tqdm(total=len(muids), leave=False, file=sys.stderr)
    threads = []
    with ThreadPoolExecutor() as executor:
        for muid in muids:
            url = (
                f"{api_url}/api/v1/org/{org_uid}/data/?src={muid}&"
                f"st={time[0]}&et={time[1]}&dt=fingerprints"
            )
            threads.append(executor.submit(get, url, api_key))
        for task in as_completed(threads):
            pbar.update(1)
            resp = task.result()
            for fprint_json in resp.iter_lines():
                fprint = json.loads(fprint_json)
                try:
                    fprint = spyctl_fprints.Fingerprint(fprint).as_dict()
                except Exception as e:
                    cli.try_log(
                        f"Error parsing fingerprint. {' '.join(e.args)}"
                    )
                    continue
                if "metadata" in fprint:
                    fingerprints.append(fprint)
    pbar.close()
    return fingerprints


def get_policies(api_url, api_key, org_uid, params=None):
    url = f"{api_url}/api/v1/org/{org_uid}/analyticspolicy/"
    params = {} if params is None else params
    if lib.METADATA_TYPE_FIELD in params:
        types = [params[lib.METADATA_TYPE_FIELD]]
    else:
        types = [lib.POL_TYPE_CONT]
    policies = []
    for type in types:
        params[lib.METADATA_TYPE_FIELD] = type
        resp = get(url, api_key, params)
        for pol_json in resp.iter_lines():
            pol_list = json.loads(pol_json)
            for pol in pol_list:
                uid = pol["uid"]
                policy = json.loads(pol["policy"])
                policy[lib.METADATA_FIELD][lib.METADATA_UID_FIELD] = uid
                policy[lib.METADATA_FIELD][lib.METADATA_CREATE_TIME] = pol[
                    "valid_from"
                ]
                policies.append(policy)
    return policies


def get_policy(api_url, api_key, org_uid, pol_uid):
    url = f"{api_url}/api/v1/org/{org_uid}/analyticspolicy/{pol_uid}"
    resp = get(url, api_key)
    policies = []
    for pol_json in resp.iter_lines():
        pol = json.loads(pol_json)
        uid = pol["uid"]
        policy = pol["policy"]
        policy[lib.METADATA_FIELD][lib.METADATA_UID_FIELD] = uid
        policies.append(policy)
    return policies


def post_new_policy(api_url, api_key, org_uid, data: Dict):
    url = f"{api_url}/api/v1/org/{org_uid}/analyticspolicy/"
    resp = post(url, data, api_key)
    # cli.try_log(resp.text)
    return resp


def put_policy_update(api_url, api_key, org_uid, pol_uid, data: Dict):
    url = f"{api_url}/api/v1/org/{org_uid}/analyticspolicy/{pol_uid}"
    resp = put(url, data, api_key)
    return resp


def delete_policy(api_url, api_key, org_uid, pol_uid):
    url = f"{api_url}/api/v1/org/{org_uid}/analyticspolicy/{pol_uid}"
    resp = delete(url, api_key)
    return resp
