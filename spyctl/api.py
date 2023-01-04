import json
import sys
import time
from typing import Callable, Dict, List, Tuple

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
        print(r.headers.get("X-Context-Uid"))
        raise RuntimeError(r.status_code, r.reason, r.text)
    return r


def post(url, data, key):
    headers = {"Authorization": f"Bearer {key}"}
    r = requests.post(url, json=data, headers=headers, timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(r.status_code, r.reason, str(r.headers), r.text)
    return r


def put(url, data, key):
    headers = {"Authorization": f"Bearer {key}"}
    r = requests.put(url, json=data, headers=headers, timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(r.status_code, r.reason)
    return r


def delete(url, key):
    headers = {"Authorization": f"Bearer {key}"}
    r = requests.delete(url, headers=headers, timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(r.status_code, r.reason)
    return r


def get_orgs(api_url, api_key, err_fn) -> List[Tuple]:
    org_uids = []
    org_names = []
    url = f"{api_url}/api/v1/org/"
    try:
        orgs_json = get(url, api_key).json()
        for org in orgs_json:
            org_uids.append(org["uid"])
            org_names.append(org["name"])
        return (org_uids, org_names)
    except RuntimeError as err:
        err_fn(*err.args)
        return None


def get_machines(api_url, api_key, org_uid, err_fn) -> List[Dict]:
    machines: Dict[str, Dict] = {}
    url = f"{api_url}/api/v1/org/{org_uid}/source/"
    try:
        source_json = get(url, api_key).json()
        for source in source_json:
            src_uid = source["uid"]
            if not src_uid.startswith("global"):
                machines[src_uid] = source
    except RuntimeError as err:
        err_fn(*err.args)
        return None
    # agents API call to find "description" (name used by the UI)
    url = f"{api_url}/api/v1/org/{org_uid}/agent/"
    try:
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
    except RuntimeError as err:
        err_fn(*err.args)
        return None
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


def get_muids(api_url, api_key, org_uid, err_fn) -> Tuple:
    last_datas = {}
    sources = {}
    # get all sources to get last data
    url = f"{api_url}/api/v1/org/{org_uid}/source/"
    try:
        source_json = get(url, api_key).json()
        for source in source_json:
            if not source["uid"].startswith("global"):
                muid = source["uid"]
                last_data = zulu.parse(source["last_data"])
                last_datas[muid] = last_data
    except RuntimeError as err:
        err_fn(*err.args)
        return None
    # get agents to get hostnames
    url = f"{api_url}/api/v1/org/{org_uid}/agent/"
    try:
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
    except RuntimeError as err:
        err_fn(*err.args)
        return None
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


def get_clusters(api_url, api_key, org_uid, err_fn):
    clusters = []
    url = f"{api_url}/api/v1/org/{org_uid}/cluster/"
    try:
        json = get(url, api_key).json()
        for cluster in json:
            if "/" not in cluster["uid"]:
                clusters.append(cluster)
    except RuntimeError as err:
        err_fn(*err.args, f"Unable to get clusters in '{org_uid}'")
        return None
    return clusters


def get_k8s_data(
    api_url, api_key, org_uid, clus_uid, err_fn, schema_key, time
):
    url = f"{api_url}/api/v1/org/{org_uid}/data/"
    url += f"?src={clus_uid}&st={time[0]}&et={time[1]}&dt=k8s"
    resp = get(url, api_key)
    for k8s_json in resp.iter_lines():
        data = json.loads(k8s_json)
        if schema_key in data["schema"]:
            yield data


def get_clust_muids(api_url, api_key, org_uid, clus_uid, time, err_fn):
    names = []
    muids = []
    for data in get_k8s_data(
        api_url, api_key, org_uid, clus_uid, err_fn, "node", time
    ):
        if "muid" not in data:
            err_fn("Data was not present in records", "try again soon?")
        if data["muid"] not in muids:
            names.append(data["metadata"]["name"])
            muids.append(data["muid"])
    return names, muids


def get_clust_namespaces(api_url, api_key, org_uid, clus_uid, time, err_fn):
    ns = set()
    for data in get_k8s_data(
        api_url, api_key, org_uid, clus_uid, err_fn, "cluster", time
    ):
        data_ns = data.get("namespaces", set())
        ns.update(data_ns)
    return sorted(ns)


def get_namespaces(api_url, api_key, org_uid, clusters, time, err_fn):
    namespaces = []
    pbar = tqdm.tqdm(total=len(clusters), leave=False, file=sys.stderr)
    for cluster in clusters:
        try:
            if "/" in cluster["uid"]:
                continue
            ns_list = get_clust_namespaces(
                api_url,
                api_key,
                org_uid,
                cluster["uid"],
                time,
                err_fn,
            )
            namespaces.append(
                {
                    "cluster_name": cluster["name"],
                    "cluster_uid": cluster["uid"],
                    "namespaces": ns_list,
                }
            )
        except RuntimeError as err:
            pbar.close()
            err_fn(
                *err.args,
                f"Unable to get namespaces for cluster '{cluster['uid']}'",
            )
        pbar.update(1)
    pbar.close()
    return namespaces


def get_pods(api_url, api_key, org_uid, clusters, time, err_fn) -> List[Dict]:
    pods = []
    pbar = tqdm.tqdm(total=len(clusters), leave=False, file=sys.stderr)
    for cluster in clusters:
        try:
            pods.extend(
                get_clust_pods(
                    api_url, api_key, org_uid, cluster["uid"], time, err_fn
                )
            )
        except RuntimeError as err:
            pbar.close()
            err_fn(
                *err.args,
                f"Unable to get pods from cluster '{cluster['uid']}'",
            )
        pbar.update(1)
    pbar.close()
    return pods


def get_clust_pods(api_url, api_key, org_uid, clus_uid, time, err_fn):
    pods = {}
    for data in get_k8s_data(
        api_url, api_key, org_uid, clus_uid, err_fn, "pod", time
    ):
        pod_id = data["id"]
        if pod_id not in pods:
            pods[pod_id] = data
        elif pods[pod_id]["time"] < data["time"]:
            pods[pod_id] = data
    return list(pods.values())


def get_fingerprints(api_url, api_key, org_uid, muids, time, err_fn):
    fingerprints = []
    pbar = tqdm.tqdm(total=len(muids), leave=False, file=sys.stderr)
    for i, muid in enumerate(muids):
        url = (
            f"{api_url}/api/v1/org/{org_uid}/data/?src={muid}&"
            f"st={time[0]}&et={time[1]}&dt=fingerprints"
        )
        try:
            resp = get(url, api_key)
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
        except RuntimeError as err:
            pbar.close()
            err_fn(*err.args, f"Unable to get fingerprints from {muid}")
            continue
        pbar.update(1)
    pbar.close()
    return fingerprints


def get_policies(api_url, api_key, org_uid, err_fn: Callable, params=None):
    url = f"{api_url}/api/v1/org/{org_uid}/analyticspolicy/"
    params = {} if params is None else params
    if lib.METADATA_TYPE_FIELD in params:
        types = [params[lib.METADATA_TYPE_FIELD]]
    else:
        types = [lib.POL_TYPE_CONT]
    policies = []
    for type in types:
        params[lib.METADATA_TYPE_FIELD] = type
        try:
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
        except RuntimeError as err:
            err_fn(*err.args, "Unable to get policies")
            return None
    return policies


def get_policy(api_url, api_key, org_uid, pol_uid, err_fn: Callable):
    url = f"{api_url}/api/v1/org/{org_uid}/analyticspolicy/{pol_uid}"
    try:
        resp = get(url, api_key)
        policies = []
        for pol_json in resp.iter_lines():
            pol = json.loads(pol_json)
            uid = pol["uid"]
            policy = pol["policy"]
            policy[lib.METADATA_FIELD][lib.METADATA_UID_FIELD] = uid
            policies.append(policy)
        return policies
    except RuntimeError as err:
        err_fn(*err.args, "Unable to get policy")
        return None


def post_new_policy(api_url, api_key, org_uid, data: Dict, err_fn: Callable):
    url = f"{api_url}/api/v1/org/{org_uid}/analyticspolicy/"
    try:
        resp = post(url, data, api_key)
        # cli.try_log(resp.text)
        return resp
    except RuntimeError as err:
        err_fn(*err.args, "Unable to upload new policy")
        return None


def put_policy_update(
    api_url, api_key, org_uid, pol_uid, data: Dict, err_fn: Callable
):
    url = f"{api_url}/api/v1/org/{org_uid}/analyticspolicy/{pol_uid}"
    try:
        resp = put(url, data, api_key)
        return resp
    except RuntimeError as err:
        err_fn(*err.args, "Unable to update policy")
        return None


def delete_policy(api_url, api_key, org_uid, pol_uid, err_fn: Callable):
    url = f"{api_url}/api/v1/org/{org_uid}/analyticspolicy/{pol_uid}"
    try:
        resp = delete(url, api_key)
    except RuntimeError as err:
        err_fn(*err.args, "Unable to delete policy")
        return None
