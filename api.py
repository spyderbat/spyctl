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
    print("Loading organizations...")
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


def get_muids(api_url, api_key, org_uid, err_fn) -> Tuple:
    print("Loading machines...")
    sources = {}
    muids = []
    hostnames = []
    # get all sources
    url = f"{api_url}/api/v1/org/{org_uid}/source/"
    try:
        source_json = get(url, api_key).json()
        for source in source_json:
            if not source['uid'].startswith("global"):
                muid = source['uid']
                last_data = zulu.parse(source['last_data'])
                sources[muid] = {
                    'muid': muid,
                    'name': source['name'],
                    'last_data': last_data
                }
    except RuntimeError as err:
        err_fn(*err.args)
        return None
    url = f"{api_url}/api/v1/org/{org_uid}/agent/"
    try:
        source_json = get(url, api_key).json()
        for source in source_json:
            if not source['uid'].startswith("global"):
                muid = source['runtime_details']['src_uid']
                hostname = source['description']
                if muid in sources:
                    if sources[muid]['name'] == "":
                        sources[muid]['name'] = hostname
    except RuntimeError as err:
        err_fn(*err.args)
        return None
    two_days_ago = zulu.now().shift(days=-2)
    for muid, data in list(sources.items()):
        if data['last_data'] < two_days_ago:
            del sources[muid]
        else:
            muids.append(muid)
            hostnames.append(data['name'])
    return muids, hostnames


def get_fingerprints(
    api_url, api_key, org_uid, muid, start_time, end_time, err_fn):
    print("Loading fingerprints...")
    url = f"{api_url}/api/v1/org/{org_uid}/data/?src={muid}&" \
        f"st={int(start_time)}&et={int(end_time)}&dt=fingerprints"
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
