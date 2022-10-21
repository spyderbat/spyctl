from typing import List, Tuple
import requests
import zulu
import json


def get(url, key):
    headers = {"Authorization": f"Bearer {key}"}
    r = requests.get(url, headers=headers)
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
            org_uids.append(org['uid'])
            org_names.append(org['name'])
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
            if not source['uid'].startswith("global"):
                muid = source['uid']
                last_data = zulu.parse(source['last_data'])
                last_datas[muid] = last_data
    except RuntimeError as err:
        err_fn(*err.args)
        return None
    # get agents to get hostnames
    url = f"{api_url}/api/v1/org/{org_uid}/agent/"
    try:
        source_json = get(url, api_key).json()
        for source in source_json:
            if not source['uid'].startswith("global"):
                muid = source['runtime_details']['src_uid']
                hostname = source['description']
                if muid in last_datas:
                    sources[muid] = {
                        'name': hostname,
                        'last_data': last_datas[muid]
                    }
    except RuntimeError as err:
        err_fn(*err.args)
        return None
    check_time = zulu.Zulu.fromtimestamp(time[0]).shift(days=-2)
    for muid, data in list(sources.items()):
        if data['last_data'] >= check_time:
            muids.append(muid)
            hostnames.append(data['name'])
    return muids, hostnames


def get_clusters(api_url, api_key, org_uid, err_fn):
    names = []
    src_uids = []
    url = f"{api_url}/api/v1/org/{org_uid}/cluster/"
    try:
        json = get(url, api_key).json()
        for cluster in json:
            names.append(cluster['name'])
            src_uids.append(cluster['uid'])
            # src_uids.append(cluster['cluster_details']['agent_uid'])
    except RuntimeError as err:
        err_fn(*err.args, f"Unable to get clusters in '{org_uid}'")
        return None
    return names, src_uids


def get_k8s_data(api_url, api_key, org_uid, clus_uid, err_fn, schema_key, time):
    url = f"{api_url}/api/v1/org/{org_uid}/data/"
    url += f"?src={clus_uid}&st={time[0]}&et={time[1]}&dt=k8s"
    try:
        resp = get(url, api_key)
        for k8s_json in resp.iter_lines():
            data = json.loads(k8s_json)
            if schema_key in data['schema']:
                yield data
    except RuntimeError as err:
        err_fn(*err.args, f"Unable to get machines from cluster '{clus_uid}'")


def get_clust_muids(api_url, api_key, org_uid, clus_uid, time, err_fn):
    names = []
    muids = []
    for data in get_k8s_data(api_url, api_key, org_uid, clus_uid, err_fn, 'node', time):
        if not 'muid' in data:
            err_fn("Data was not present in records", "try again soon?")
        if data['muid'] not in muids:
            names.append(data['metadata']['name'])
            muids.append(data['muid'])
    return names, muids


def get_clust_namespaces(api_url, api_key, org_uid, clus_uid, time, err_fn):
    latest = {"time": "0"}
    for data in get_k8s_data(api_url, api_key, org_uid, clus_uid, err_fn, 'cluster', time):
        if float(latest['time']) < float(data['time']):
            latest = data
    return sorted(latest['namespaces'])


def get_clust_pods(api_url, api_key, org_uid, clus_uid, time, err_fn):
    pods = {}
    for data in get_k8s_data(api_url, api_key, org_uid, clus_uid, err_fn, 'pod', time):
        namespace = data['metadata']['namespace']
        muid = data.get('muid', 'unknown')
        if not namespace in pods:
            pods[namespace] = [data['metadata']['name']], [data['id']], [muid]
            continue
        if not data['id'] in pods[namespace][1]:
            if data['status'] != 'closed':
                pods[namespace][0].append(data['metadata']['name'])
                pods[namespace][1].append(data['id'])
                pods[namespace][2].append(muid)
        else:
            idx = pods[namespace][1].index(data['id'])
            if pods[namespace][2][idx] == "unknown":
                pods[namespace][2][idx] = muid
            if data['status'] == 'closed':
                for i in range(3):
                    pods[namespace][i].pop(idx)
    # for ns, lst in pods.items():
    #     print("namespace:", ns)
    #     for i, muid in enumerate(lst[2]):
    #         if muid == "unknown":
    #             print(lst[0][i])
    return pods

def get_fingerprints(api_url, api_key, org_uid, muid, time, err_fn):
    url = f"{api_url}/api/v1/org/{org_uid}/data/?src={muid}&" \
        f"st={time[0]}&et={time[1]}&dt=fingerprints"
    try:
        fingerprints = []
        resp = get(url, api_key)
        for fprint_json in resp.iter_lines():
            fprint = json.loads(fprint_json)
            if 'metadata' in fprint:
                fingerprints.append(fprint)
        return fingerprints
    except RuntimeError as err:
        err_fn(*err.args, f"Unable to get fingerprints from {muid}")
        return None
