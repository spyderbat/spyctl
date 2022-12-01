import json
from typing import List, Tuple, Dict, Callable
import spyctl.policies as p
import spyctl.cli as cli

import requests
import zulu

# Get policy parameters
GET_POL_TYPE = "type"
GET_POL_HAS_TAGS = "has_tags"
GET_POL_NAME_CONTAINS = "name_contains"
GET_POL_POLICY_CONTAINS = "policy_contains"
GET_POL_SELECTOR_CONTAINS = "selector_contains"
GET_POL_UID_EQUALS = "uid_equals"


# https://requests.readthedocs.io/en/latest/user/advanced/#timeouts
# connection timeout, read timeout
TIMEOUT = (6.10, 27)


def get(url, key, params=None):
    headers = {"Authorization": f"Bearer {key}"}
    r = requests.get(url, headers=headers, timeout=TIMEOUT, params=params)
    if r.status_code != 200:
        raise RuntimeError(r.status_code, r.reason, r.text)
    return r


def post(url, data, key):
    headers = {"Authorization": f"Bearer {key}"}
    r = requests.post(url, data, headers=headers, timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(r.status_code, r.reason, str(r.headers), r.text)
    return r


def put(url, data, key):
    headers = {"Authorization": f"Bearer {key}"}
    r = requests.put(url, data, headers=headers, timeout=TIMEOUT)
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


def get_muids(api_url, api_key, org_uid, time, err_fn) -> Tuple:
    last_datas = {}
    sources = {}
    muids = []
    hostnames = []
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
    check_time = zulu.Zulu.fromtimestamp(time[0]).shift(days=-2)
    for muid, data in list(sources.items()):
        if data["last_data"] >= check_time:
            muids.append(muid)
            hostnames.append(data["name"])
    return muids, hostnames


def get_clusters(api_url, api_key, org_uid, err_fn):
    names = []
    src_uids = []
    url = f"{api_url}/api/v1/org/{org_uid}/cluster/"
    try:
        json = get(url, api_key).json()
        for cluster in json:
            names.append(cluster["name"])
            src_uids.append(cluster["uid"])
            # src_uids.append(cluster['cluster_details']['agent_uid'])
    except RuntimeError as err:
        err_fn(*err.args, f"Unable to get clusters in '{org_uid}'")
        return None
    return names, src_uids


def get_k8s_data(
    api_url, api_key, org_uid, clus_uid, err_fn, schema_key, time
):
    url = f"{api_url}/api/v1/org/{org_uid}/data/"
    url += f"?src={clus_uid}&st={time[0] - 60*60}&et={time[1]}&dt=k8s"
    try:
        resp = get(url, api_key)
        for k8s_json in resp.iter_lines():
            data = json.loads(k8s_json)
            if schema_key in data["schema"]:
                yield data
    except RuntimeError as err:
        err_fn(*err.args, f"Unable to get machines from cluster '{clus_uid}'")


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
    latest = {"time": "0"}
    for data in get_k8s_data(
        api_url, api_key, org_uid, clus_uid, err_fn, "cluster", time
    ):
        if float(latest["time"]) < float(data["time"]):
            latest = data
    return sorted(latest.get(["namespaces"], []))


def get_clust_pods(api_url, api_key, org_uid, clus_uid, time, err_fn):
    pods = {}
    for data in get_k8s_data(
        api_url, api_key, org_uid, clus_uid, err_fn, "pod", time
    ):
        namespace = data["metadata"]["namespace"]
        muid = data.get("muid", "unknown")
        if namespace not in pods:
            pods[namespace] = [data["metadata"]["name"]], [data["id"]], [muid]
            continue
        if not data["id"] in pods[namespace][1]:
            if data["status"] != "closed":
                pods[namespace][0].append(data["metadata"]["name"])
                pods[namespace][1].append(data["id"])
                pods[namespace][2].append(muid)
        else:
            idx = pods[namespace][1].index(data["id"])
            if pods[namespace][2][idx] == "unknown":
                pods[namespace][2][idx] = muid
            if data["status"] == "closed" and data["time"] < time[0]:
                for i in range(3):
                    pods[namespace][i].pop(idx)
    # for ns, lst in pods.items():
    #     print("namespace:", ns)
    #     for i, muid in enumerate(lst[2]):
    #         if muid == "unknown":
    #             print(lst[0][i])
    return pods


def get_fingerprints(api_url, api_key, org_uid, muid, time, err_fn):
    url = (
        f"{api_url}/api/v1/org/{org_uid}/data/?src={muid}&"
        f"st={time[0] - 60*60}&et={time[1]}&dt=fingerprints"
    )
    try:
        fingerprints = []
        resp = get(url, api_key)
        for fprint_json in resp.iter_lines():
            fprint = json.loads(fprint_json)
            if "metadata" in fprint:
                fingerprints.append(fprint)
        return fingerprints
    except RuntimeError as err:
        err_fn(*err.args, f"Unable to get fingerprints from {muid}")
        return None


def get_policies(api_url, api_key, org_uid, err_fn: Callable, params):
    url = f"{api_url}/api/v1/org/{org_uid}/analyticspolicy/"
    try:
        resp = get(url, api_key, params)
        policies = []
        for pol_json in resp.iter_lines():
            pol_list = json.loads(pol_json)
            for pol in pol_list:
                print(pol)
                uid = pol["uid"]
                policy = pol["policy"]
                policy[p.K8S_METADATA_FIELD][p.METADATA_UID_FIELD] = uid
                policies.append(policy)
        return policies
    except RuntimeError as err:
        err_fn(*err.args, "Unable to get policies")
        return None


def get_policy(api_url, api_key, org_uid, pol_uid, err_fn: Callable):
    url = f"{api_url}/api/v1/org/{org_uid}/analyticspolicy/{pol_uid}"
    try:
        resp = get(url, api_key)
        policies = []
        for pol_json in resp.iter_lines():
            pol = json.loads(pol_json)
            uid = pol["uid"]
            policy = pol["policy"]
            policy[p.K8S_METADATA_FIELD][p.METADATA_UID_FIELD] = uid
            policies.append(policy)
        return policies
    except RuntimeError as err:
        err_fn(*err.args, "Unable to get policy")
        return None


def post_new_policy(api_url, api_key, org_uid, data, err_fn: Callable):
    url = f"{api_url}/api/v1/org/{org_uid}/analyticspolicy/"
    try:
        resp = post(url, data, api_key)
        cli.try_log(resp.headers, resp.text)
        return resp
    except RuntimeError as err:
        err_fn(*err.args, "Unable to upload new policy")
        return None


def put_policy_update(
    api_url, api_key, org_uid, pol_uid, data, err_fn: Callable
):
    url = f"{api_url}/api/v1/org/{org_uid}/analyticspolicy/{pol_uid}"
    try:
        resp = put(url, data, api_key)
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
