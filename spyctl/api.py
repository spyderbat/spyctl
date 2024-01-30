import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, Generator, List, Optional, Tuple, Union

import requests
import tqdm
import zulu

import spyctl.cli as cli
import spyctl.spyctl_lib as lib
from spyctl.cache_dict import CacheDict

# Get policy parameters
GET_POL_TYPE = "type"
GET_POL_HAS_TAGS = "has_tags"
GET_POL_NAME_CONTAINS = "name_contains"
GET_POL_POLICY_CONTAINS = "policy_contains"
GET_POL_SELECTOR_CONTAINS = "selector_contains"
GET_POL_UID_EQUALS = "uid_equals"


# https://requests.readthedocs.io/en/latest/user/advanced/#timeouts
# connection timeout, read timeout
TIMEOUT = (30, 300)

AUTO_HIDE_TIME = zulu.now().shift(days=-1)
MAX_TIME_RANGE_SECS = 43200  # 12 hours
NAMESPACES_MAX_RANGE_SECS = 2000
TIMEOUT_MSG = "A timeout occurred during the API request. "


class NotFoundException(ValueError):
    pass


# ----------------------------------------------------------------- #
#                           API Primitives                          #
# ----------------------------------------------------------------- #


def get(url, key, params=None, raise_notfound=False):
    if key:
        headers = {
            "Authorization": f"Bearer {key}",
            "content-type": "application/json",
            "accept": "application/json",
        }
    else:
        headers = None
    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT, params=params)
    except requests.exceptions.Timeout as e:
        cli.err_exit(TIMEOUT_MSG + str(*e.args))
    context_uid = r.headers.get("x-context-uid", "No context uid found.")
    if lib.DEBUG:
        print(
            f"Request to {url}\n\tcontext_uid: {context_uid}"
            f"\n\tstatus: {r.status_code}"
        )
    if r.status_code == 404 and raise_notfound:
        raise NotFoundException()
    if r.status_code != 200:
        if "x-context-uid" in r.headers:
            context_uid = r.headers["x-context-uid"]
        else:
            context_uid = "No context uid found."
        msg = [f"{r.status_code}, {r.reason}", f"\tContext UID: {context_uid}"]
        if r.text:
            try:
                error = json.loads(r.text)
                if "msg" in error:
                    msg.append(error["msg"])
                else:
                    msg.append(f"{r.text}")
            except Exception:
                msg.append(f"{r.text}")
        msg = "\n".join(msg)
        cli.err_exit(msg)
    return r


def post(url, data, key, raise_notfound=False):
    headers = {"Authorization": f"Bearer {key}"}
    try:
        r = requests.post(url, json=data, headers=headers, timeout=TIMEOUT)
    except requests.exceptions.Timeout as e:
        cli.err_exit(TIMEOUT_MSG + str(e.args))
    context_uid = r.headers.get("x-context-uid", "No context uid found.")
    if lib.DEBUG:
        print(
            f"Request to {url}\n\tcontext_uid: {context_uid}"
            f"\n\tstatus: {r.status_code}"
        )
    if r.status_code == 404 and raise_notfound:
        raise NotFoundException()
    if r.status_code != 200:
        if "x-context-uid" in r.headers:
            context_uid = r.headers["x-context-uid"]
        else:
            context_uid = "No context uid found."
        msg = [f"{r.status_code}, {r.reason}", f"\tContext UID: {context_uid}"]
        if r.text:
            try:
                error = json.loads(r.text)
                if "msg" in error:
                    msg.append(error["msg"])
                else:
                    msg.append(f"{r.text}")
            except Exception:
                msg.append(f"{r.text}")
        msg = "\n".join(msg)
        cli.err_exit(msg)
    return r


def put(url, data, key):
    headers = {"Authorization": f"Bearer {key}"}
    try:
        r = requests.put(url, json=data, headers=headers, timeout=TIMEOUT)
    except requests.exceptions.Timeout as e:
        cli.err_exit(TIMEOUT_MSG + str(e.args))
    context_uid = r.headers.get("x-context-uid", "No context uid found.")
    if lib.DEBUG:
        print(
            f"Request to {url}\n\tcontext_uid: {context_uid}"
            f"\n\tstatus: {r.status_code}"
        )
    if r.status_code != 200:
        if "x-context-uid" in r.headers:
            context_uid = r.headers["x-context-uid"]
        else:
            context_uid = "No context uid found."
        msg = [f"{r.status_code}, {r.reason}", f"\tContext UID: {context_uid}"]
        if r.text:
            try:
                error = json.loads(r.text)
                if "msg" in error:
                    msg.append(error["msg"])
                else:
                    msg.append(f"{r.text}")
            except Exception:
                msg.append(f"{r.text}")
        msg = "\n".join(msg)
        cli.err_exit(msg)
    return r


def delete(url, key):
    headers = {"Authorization": f"Bearer {key}"}
    try:
        r = requests.delete(url, headers=headers, timeout=TIMEOUT)
    except requests.exceptions.Timeout as e:
        cli.err_exit(TIMEOUT_MSG + str(e.args))
    context_uid = r.headers.get("x-context-uid", "No context uid found.")
    if lib.DEBUG:
        print(
            f"Request to {url}\n\tcontext_uid: {context_uid}"
            f"\n\tstatus: {r.status_code}"
        )
    if r.status_code != 200:
        if "x-context-uid" in r.headers:
            context_uid = r.headers["x-context-uid"]
        else:
            context_uid = "No context uid found."
        msg = [f"{r.status_code}, {r.reason}", f"\tContext UID: {context_uid}"]
        if r.text:
            try:
                error = json.loads(r.text)
                if "msg" in error:
                    msg.append(error["msg"])
                else:
                    msg.append(f"{r.text}")
            except Exception:
                msg.append(f"{r.text}")
        msg = "\n".join(msg)
        cli.err_exit(msg)
    return r


# ----------------------------------------------------------------- #
#                     Main Retrieval Functions                      #
# ----------------------------------------------------------------- #


# Elastic Retrieval
def get_object_by_id(
    api_url,
    api_key,
    org_uid,
    id: str,
    schema: str,
    time: Tuple[float, float] = None,
    datatype="spydergraph",
):
    if time:
        hour_floor = lib.truncate_hour_epoch(time[0])
        data = {
            "data_type": datatype,
            "org_uid": org_uid,
            "query": f'(id:"{id}") AND (schema:"{schema}")'
            f" AND ((((valid_to:>{time[0]})"
            f' OR ((NOT status:"closed") AND time:>={hour_floor}))'
            f" AND valid_from:<{time[1]}) OR (time:[{time[0]} TO {time[1]}]"
            f" AND NOT _exists_:valid_to))",
            "query_from": 0,
            "query_size": 1,
        }
    else:
        data = {
            "data_type": datatype,
            "org_uid": org_uid,
            "query": f'(id:"{id}")',
            "query_from": 0,
            "query_size": 1,
        }
    url = (
        f"{api_url}/api/v1/source/query/"
        "?ui_tag=SearchLoadAllSchemaTypesInOneQuery"
    )
    return post(url, data, api_key)


DEFAULT_CACHE_DICT_LEN = 10000


# Source-based Retrieval
def retrieve_data(
    api_url: str,
    api_key: str,
    org_uid: str,
    sources: Union[str, List[str]],
    datatype: str,
    schema: str,
    time: Tuple[float, float],
    raise_notfound=False,
    pipeline: List = None,
    url: str = "api/v1/source/query/",
    disable_pbar=False,
    limit_mem=True,
    disable_pbar_on_first=False,
    api_data: Dict = None,
):
    """This is the defacto data retrieval function. Most queries that don't
    target the SQL db can be executed with this function. It enforces limited
    memory usage unless told otherwise, shows a progress bar unless told
    otherwise, and yields records one at a time. The data returned is unsorted.

    Args:
        api_url (str): Top-most part of the API url -- from context
        api_key (str): Key to access the API -- from context
        org_uid (str): Org to get data from -- from context
        source (str, List[str]): The uid(s) that the data are tied to
        datatype (str): The data stream to look for the data in
        schema (str): A prefix of the schema for the desired objects
            (ex. model_connection, model_process)
        time (Tuple[float, float]): A tuple with (starting time, ending time)
        raise_notfound (bool, optional): Error to raise if the API throws an
            404 error. Defaults to False.
        pipeline (list, optional): Filtering done by the api.
            Defaults to None.
        url (str, optional): Alternative url path (ex. f"{api_url}/{url}").
            Defaults to "api/v1/source/query/".
        disable_pbar (bool, optional): Does not show the progress bar if set
            to True. Defaults to False.
        limit_mem (bool, optional): Limits the memory usage on the Latest
            Model calculation. If True we may return duplicate objects.
            Defaults to True.
        disable_pbar_on_first (bool, optional): Closes and clears the progress
            bar after first item is returned. Defaults to False.
        api_data (dict, optional): Alternative data to pass to the API.

    Yields:
        Iterator[dict]: An iterator over retrieved objects.
    """

    progress_bar_tracker: List[tqdm.tqdm] = []
    popped_off_cache = []

    def yield_on_del(_, value):
        if disable_pbar_on_first:
            progress_bar_tracker[0].close()
        popped_off_cache.append(value)

    cache_len = DEFAULT_CACHE_DICT_LEN if limit_mem else None
    data = CacheDict(cache_len=cache_len, on_del=yield_on_del)

    def new_version(id: str, obj: dict) -> bool:
        new_v = obj.get("version")
        if not new_v:
            return True
        old_obj: Dict = data.get(id)
        if not old_obj:
            return True
        old_v = old_obj.get("version")
        if not old_v:
            return True
        return new_v > old_v

    if isinstance(sources, str):
        sources = [sources]

    for resp in threadpool_progress_bar_time_blocks(
        sources,
        time,
        lambda src_uid, time_tup: get_filtered_data(
            api_url,
            api_key,
            org_uid,
            src_uid,
            datatype,
            schema,
            time_tup,
            raise_notfound,
            pipeline,
            url,
            api_data,
        ),
        disable_pbar=disable_pbar,
        pbar_tracker=progress_bar_tracker,
    ):
        if not resp:
            continue
        for json_obj in resp.iter_lines():
            obj = json.loads(json_obj)
            id = obj.get("id")
            if id:
                if new_version(id, obj):
                    data[id] = obj
                    while len(popped_off_cache) > 0:
                        yield popped_off_cache.pop()
            else:
                yield obj
    else:
        while len(data) > 0:
            yield data.popitem()[1]


def get_filtered_data(
    api_url,
    api_key,
    org_uid,
    source,
    datatype,
    schema,
    time,
    raise_notfound=False,
    pipeline=None,
    url="api/v1/source/query/",
    api_data=None,
) -> Optional[requests.Response]:
    """This function formats and makes a post request following the
    "source query" format. If a pipeline is not provided, this function will
    craft a basic one.

    Args:
        api_url (str): Top-most part of the API url -- from context
        api_key (str): Key to access the API -- from context
        org_uid (str): Org to get data from -- from context
        source (str, List[str]): The uid(s) that the data are tied to
        datatype (str): The data stream to look for the data in
        schema (str): A prefix of the schema for the desired objects
            (ex. model_connection, model_process)
        time (Tuple[float, float]): A tuple with (starting time, ending time)
        raise_notfound (bool, optional): Error to raise if the API throws an
            error. Defaults to False.
        pipeline (_type_, optional): Filtering done by the api.
            Defaults to None.
        url (_type_, optional): Alternative url path (ex. f"{api_url}/{url}").
            Defaults to "api/v1/source/query/".

    Returns:
        Response: The http response from the request.
    """
    url = f"{api_url}/{url}"
    if not api_data:
        data = {
            "start_time": time[0],
            "end_time": time[1],
            "data_type": datatype,
            "pipeline": [{"filter": {"schema": schema}}, {"latest_model": {}}],
        }
        if org_uid:
            data["org_uid"] = org_uid
        if pipeline:
            data["pipeline"] = pipeline
        if source:
            data["src_uid"] = source
    else:
        api_data["src_uid"] = source
        data = api_data
    try:
        return post(url, data, api_key, raise_notfound)
    except NotFoundException:
        return None


def threadpool_progress_bar_time_blocks(
    args_per_thread: List[str],
    time,
    function: Callable,
    max_time_range=MAX_TIME_RANGE_SECS,
    disable_pbar=False,
    pbar_tracker: List = [],
) -> str:
    """This function runs a multi-threaded task such as making multiple API
    requests simultaneously. By default it shows a progress bar. This is a
    specialized function for the Spyderbat API because it will break up
    api-requests into time blocks of a maximum size if necessary. The
    Spyderbat API doesn't like queries spanning over 24 hours so we break them
    into smaller chunks.

    Args:
        args_per_thread (List[str]): The args to pass to each thread example:
            list of source uids.
        time (Tuple[float, float]): A tuple containing the start and end time
            of the task
        function (Callable): The function that each thread will perform
        max_time_range (_type_, optional): The maximum size of a time block.
            Defaults to MAX_TIME_RANGE_SECS.
        disable_pbar (bool, optional): Disable the progress bar.
            Defaults to False.
        pbar_tracker (list): A list that allows calling functions to control
            the pbar.

    Yields:
        Iterator[any]: The return value from the thread task.
    """
    t_blocks = time_blocks(time, max_time_range)
    args_per_thread = [
        [arg, t_block] for arg in args_per_thread for t_block in t_blocks
    ]
    pbar = tqdm.tqdm(
        total=len(args_per_thread),
        leave=False,
        file=sys.stderr,
        disable=disable_pbar,
    )
    pbar_tracker.clear()
    pbar_tracker.append(pbar)
    threads = []
    with ThreadPoolExecutor() as executor:
        for args in args_per_thread:
            threads.append(executor.submit(function, *args))
        for task in as_completed(threads):
            pbar.update(1)
            yield task.result()


def threadpool_progress_bar(
    args_per_thread: Union[List[List], List[str]],
    function: Callable,
    unpack_args=False,
):
    """A simplified version of the above function. In most cases it is
    best to use the time_blocks version unless you really know what you're
    doing.

    Args:
        args_per_thread (Union[List[List], List[str]]): The args to pass to
            each thread example:
            list of source uids.
        function (Callable): The function that each thread will perform
        unpack_args (bool, optional): _description_. Defaults to False.

    Yields:
        Iterator[any]: The return value from the thread task.
    """
    pbar = tqdm.tqdm(total=len(args_per_thread), leave=False, file=sys.stderr)
    threads = []
    with ThreadPoolExecutor() as executor:
        for args in args_per_thread:
            if unpack_args:
                threads.append(executor.submit(function, *args))
            else:
                threads.append(executor.submit(function, args))
        for task in as_completed(threads):
            pbar.update(1)
            yield task.result()


def time_blocks(
    time_tup: Tuple, max_time_range=MAX_TIME_RANGE_SECS
) -> List[Tuple]:
    """Takes a time tuple (start, end) in epoch time and converts
    it to smaller chunks if necessary.

    Args:
        time_tup (Tuple): start, end

    Returns:
        List[Tuple]: A list of (start, end) tuples to be used in api
            queries
    """
    st, et = time_tup
    if et - st > max_time_range:
        rv = []
        while et - st > max_time_range:
            et2 = min(et, st + max_time_range)
            rv.append((st, et2))
            st = et2
        rv.append((st, et))
        return rv
    else:
        return [time_tup]


# ----------------------------------------------------------------- #
#                        SQL-Based Resources                        #
# ----------------------------------------------------------------- #


def get_clusters(api_url, api_key, org_uid) -> List[Dict]:
    clusters = []
    url = f"{api_url}/api/v1/org/{org_uid}/cluster/"
    json = get(url, api_key).json()
    for cluster in json:
        if "/" not in cluster["uid"]:
            clusters.append(cluster)
    return clusters


def get_notification_policy(api_url, api_key, org_uid) -> Dict:
    url = f"{api_url}/api/v1/org/{org_uid}/notification_policy/"
    json = get(url, api_key).json()
    return json


def put_notification_policy(api_url, api_key, org_uid, notification_pol):
    url = f"{api_url}/api/v1/org/{org_uid}/notification_policy/"
    resp = put(url, notification_pol, api_key)
    return resp


def post_test_notification(api_url, api_key, org_uid, target_name):
    url = f"{api_url}/api/v1/org/{org_uid}/notification_policy/test_target"
    resp = post(url, {"target": target_name}, api_key)
    return resp


def get_sources(api_url, api_key, org_uid) -> List[Dict]:
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


def get_orgs(api_url, api_key) -> List[Tuple]:
    org_uids = []
    org_names = []
    url = f"{api_url}/api/v1/org/"
    orgs_json = get(url, api_key).json()
    for org in orgs_json:
        org_uids.append(org["uid"])
        org_names.append(org["name"])
    return (org_uids, org_names)


# ----------------------------------------------------------------- #
#                       Source-Based Resources                      #
# ----------------------------------------------------------------- #


def get_agents(
    api_url,
    api_key,
    org_uid,
    muids,
    time,
    pipeline=None,
    limit_mem: bool = False,
    disable_pbar_on_first: bool = False,
) -> Generator[Dict, None, None]:
    try:
        datatype = lib.DATATYPE_AGENTS
        schema = lib.MODEL_AGENT_SCHEMA_PREFIX
        for agent in retrieve_data(
            api_url,
            api_key,
            org_uid,
            muids,
            datatype,
            schema,
            time,
            pipeline=pipeline,
            limit_mem=limit_mem,
            disable_pbar_on_first=disable_pbar_on_first,
        ):
            yield agent
    except KeyboardInterrupt:
        __log_interrupt()


def get_connections(
    api_url,
    api_key,
    org_uid,
    muids,
    time,
    pipeline=None,
    limit_mem: bool = False,
    disable_pbar_on_first: bool = False,
) -> Generator[Dict, None, None]:
    try:
        datatype = lib.DATATYPE_SPYDERGRAPH
        schema = lib.MODEL_CONNECTION_PREFIX
        for connection in retrieve_data(
            api_url,
            api_key,
            org_uid,
            muids,
            datatype,
            schema,
            time,
            pipeline=pipeline,
            limit_mem=limit_mem,
            disable_pbar_on_first=disable_pbar_on_first,
        ):
            yield connection
    except KeyboardInterrupt:
        __log_interrupt()


def get_connection_bundles(
    api_url,
    api_key,
    org_uid,
    sources,
    time,
    pipeline=None,
    limit_mem: bool = False,
    disable_pbar_on_first: bool = False,
):
    try:
        if sources and sources[0].startswith("clus:"):
            datatype = lib.DATATYPE_K8S
        else:
            datatype = lib.DATATYPE_SPYDERGRAPH
        schema = lib.MODEL_CONN_BUN_PREFIX
        for conn_bun in retrieve_data(
            api_url,
            api_key,
            org_uid,
            sources,
            datatype,
            schema,
            time,
            pipeline=pipeline,
            limit_mem=limit_mem,
            disable_pbar_on_first=disable_pbar_on_first,
        ):
            yield conn_bun
    except KeyboardInterrupt:
        __log_interrupt()


def get_containers(
    api_url,
    api_key,
    org_uid,
    sources,
    time,
    pipeline=None,
    limit_mem: bool = False,
    disable_pbar_on_first: bool = False,
) -> Generator[Dict, None, None]:
    try:
        if sources and sources[0].startswith("clus"):
            datatype = lib.DATATYPE_K8S
        else:
            datatype = lib.DATATYPE_SPYDERGRAPH
        schema = lib.MODEL_CONTAINER_PREFIX
        for container in retrieve_data(
            api_url,
            api_key,
            org_uid,
            sources,
            datatype,
            schema,
            time,
            raise_notfound=True,
            pipeline=pipeline,
            limit_mem=limit_mem,
            disable_pbar_on_first=disable_pbar_on_first,
        ):
            yield container
    except KeyboardInterrupt:
        __log_interrupt()


def get_daemonsets(
    api_url,
    api_key,
    org_uid,
    clusters,
    time,
    pipeline=None,
    limit_mem: bool = False,
    disable_pbar_on_first: bool = False,
) -> Generator[Dict, None, None]:
    try:
        datatype = lib.DATATYPE_K8S
        schema = lib.MODEL_DAEMONSET_PREFIX
        for daemonset in retrieve_data(
            api_url,
            api_key,
            org_uid,
            clusters,
            datatype,
            schema,
            time,
            pipeline=pipeline,
            raise_notfound=True,
            limit_mem=limit_mem,
            disable_pbar_on_first=disable_pbar_on_first,
        ):
            yield daemonset
    except KeyboardInterrupt:
        __log_interrupt()


def get_deployments(
    api_url,
    api_key,
    org_uid,
    clusters,
    time,
    pipeline=None,
    limit_mem: bool = False,
    disable_pbar_on_first: bool = False,
) -> Generator[Dict, None, None]:
    try:
        datatype = lib.DATATYPE_K8S
        schema = lib.MODEL_DEPLOYMENT_PREFIX
        for deployment in retrieve_data(
            api_url,
            api_key,
            org_uid,
            clusters,
            datatype,
            schema,
            time,
            raise_notfound=True,
            pipeline=pipeline,
            limit_mem=limit_mem,
            disable_pbar_on_first=disable_pbar_on_first,
        ):
            yield deployment
    except KeyboardInterrupt:
        __log_interrupt()


def get_deviations(
    api_url,
    api_key,
    org_uid,
    policy_uids,
    time,
    pipeline=None,
    limit_mem: bool = False,
    disable_pbar=False,
    disable_pbar_on_first: bool = False,
) -> Generator[Dict, None, None]:
    try:
        datatype = lib.DATATYPE_AUDIT
        schema = (
            f"{lib.EVENT_AUDIT_PREFIX}:"
            f"{lib.EVENT_AUDIT_SUBTYPE_MAP['deviation']}"
        )
        url = f"api/v1/org/{org_uid}/analyticspolicy/logs"
        for deviation in retrieve_data(
            api_url,
            api_key,
            org_uid,
            policy_uids,
            datatype,
            schema,
            time,
            url=url,
            raise_notfound=True,
            pipeline=pipeline,
            limit_mem=limit_mem,
            disable_pbar=disable_pbar,
            disable_pbar_on_first=disable_pbar_on_first,
        ):
            yield deviation
    except KeyboardInterrupt:
        __log_interrupt()


def get_fingerprints(
    api_url,
    api_key,
    org_uid,
    sources,
    time,
    fprint_type=None,
    pipeline=None,
    limit_mem: bool = False,
    disable_pbar_on_first: bool = False,
) -> Generator[Dict, None, None]:
    try:
        datatype = lib.DATATYPE_FINGERPRINTS
        if fprint_type:
            schema = (
                f"{lib.MODEL_FINGERPRINT_PREFIX}:"
                f"{lib.MODEL_FINGERPRINT_SUBTYPE_MAP[fprint_type]}"
            )
        else:
            schema = lib.MODEL_FINGERPRINT_PREFIX
        for fingerprint in retrieve_data(
            api_url,
            api_key,
            org_uid,
            sources,
            datatype,
            schema,
            time,
            pipeline=pipeline,
            limit_mem=limit_mem,
            disable_pbar_on_first=disable_pbar_on_first,
        ):
            if fingerprint.get("metadata", {}).get("type") not in {
                lib.POL_TYPE_CONT,
                lib.POL_TYPE_SVC,
            }:
                continue
            yield fingerprint
    except KeyboardInterrupt:
        __log_interrupt()


def get_guardian_fingerprints(
    api_url,
    api_key,
    org_uid,
    sources,
    time,
    fprint_type=None,
    unique=False,
    limit_mem: bool = False,
    disable_pbar_on_first: bool = False,
    expr=None,
    **filters,
):
    if fprint_type == lib.POL_TYPE_SVC:
        fprint_type = "linux_svc"
    api_data = {
        "org_uid": org_uid,
        "start_time": time[0],
        "end_time": time[1],
        "fingerprint_type": fprint_type,
        "unique": False,
        "expr": expr,
        **filters,
    }
    url = "api/v1/fingerprint/guardian/query"
    try:
        for fingerprint in retrieve_data(
            api_url,
            api_key,
            org_uid,
            sources,
            None,
            None,
            time,
            pipeline=None,
            url=url,
            disable_pbar_on_first=disable_pbar_on_first,
            api_data=api_data,
            limit_mem=limit_mem,
        ):
            yield fingerprint
    except KeyboardInterrupt:
        __log_interrupt()


def get_machines(
    api_url,
    api_key,
    org_uid,
    muids,
    time,
    pipeline=None,
    limit_mem: bool = False,
    disable_pbar_on_first: bool = False,
) -> Generator[Dict, None, None]:
    try:
        datatype = lib.DATATYPE_SPYDERGRAPH
        schema = lib.MODEL_MACHINE_PREFIX
        for machine in retrieve_data(
            api_url,
            api_key,
            org_uid,
            muids,
            datatype,
            schema,
            time,
            pipeline=pipeline,
            limit_mem=limit_mem,
            disable_pbar_on_first=disable_pbar_on_first,
        ):
            yield machine
    except KeyboardInterrupt:
        __log_interrupt()


def get_namespaces(
    api_url,
    api_key,
    org_uid,
    clusters,
    time,
    pipeline=None,
    disable_pbar_on_first: bool = False,
) -> Generator[Dict, None, None]:
    try:
        datatype = lib.DATATYPE_K8S
        schema = lib.MODEL_CLUSTER_PREFIX
        namespaces = list(
            retrieve_data(
                api_url,
                api_key,
                org_uid,
                clusters,
                datatype,
                schema,
                time,
                raise_notfound=True,
                pipeline=pipeline,
                limit_mem=False,
                disable_pbar_on_first=disable_pbar_on_first,
            )
        )
        for namespace in namespaces:
            yield namespace
    except KeyboardInterrupt:
        __log_interrupt()


def get_nodes(
    api_url,
    api_key,
    org_uid,
    clusters,
    time,
    pipeline=None,
    limit_mem: bool = False,
    disable_pbar_on_first: bool = False,
) -> Generator[Dict, None, None]:
    try:
        datatype = lib.DATATYPE_K8S
        schema = lib.MODEL_NODE_PREFIX
        for node in retrieve_data(
            api_url,
            api_key,
            org_uid,
            clusters,
            datatype,
            schema,
            time,
            raise_notfound=True,
            pipeline=pipeline,
            limit_mem=limit_mem,
            disable_pbar_on_first=disable_pbar_on_first,
        ):
            yield node
    except KeyboardInterrupt:
        __log_interrupt()


def get_opsflags(
    api_url,
    api_key,
    org_uid,
    sources,
    time,
    pipeline=None,
    limit_mem: bool = False,
    disable_pbar_on_first: bool = False,
) -> Generator[Dict, None, None]:
    try:
        if sources and sources[0].startswith("clus:"):
            datatype = lib.DATATYPE_K8S
        else:
            datatype = lib.DATATYPE_REDFLAGS
        schema = lib.EVENT_OPSFLAG_PREFIX
        for opsflag in retrieve_data(
            api_url,
            api_key,
            org_uid,
            sources,
            datatype,
            schema,
            time,
            pipeline=pipeline,
            limit_mem=limit_mem,
            disable_pbar_on_first=disable_pbar_on_first,
        ):
            yield opsflag
    except KeyboardInterrupt:
        __log_interrupt()


def get_pods(
    api_url,
    api_key,
    org_uid,
    clusters,
    time,
    pipeline=None,
    limit_mem: bool = False,
    disable_pbar_on_first: bool = False,
) -> Generator[Dict, None, None]:
    try:
        datatype = lib.DATATYPE_K8S
        schema = lib.MODEL_POD_PREFIX
        for pod in retrieve_data(
            api_url,
            api_key,
            org_uid,
            clusters,
            datatype,
            schema,
            time,
            raise_notfound=True,
            pipeline=pipeline,
            limit_mem=limit_mem,
            disable_pbar_on_first=disable_pbar_on_first,
        ):
            yield pod
    except KeyboardInterrupt:
        __log_interrupt()


def get_processes(
    api_url,
    api_key,
    org_uid,
    muids,
    time,
    pipeline=None,
    limit_mem: bool = False,
    disable_pbar_on_first: bool = False,
) -> Generator[Dict, None, None]:
    try:
        datatype = lib.DATATYPE_SPYDERGRAPH
        schema = lib.MODEL_PROCESS_PREFIX
        for process in retrieve_data(
            api_url,
            api_key,
            org_uid,
            muids,
            datatype,
            schema,
            time,
            pipeline=pipeline,
            limit_mem=limit_mem,
            disable_pbar_on_first=disable_pbar_on_first,
        ):
            yield process
    except KeyboardInterrupt:
        __log_interrupt()


def get_replicaset(
    api_url,
    api_key,
    org_uid,
    clusters,
    time,
    pipeline=None,
    limit_mem: bool = False,
    disable_pbar_on_first: bool = False,
) -> Generator[Dict, None, None]:
    try:
        datatype = lib.DATATYPE_K8S
        schema = lib.MODEL_REPLICASET_PREFIX
        for replicaset in retrieve_data(
            api_url,
            api_key,
            org_uid,
            clusters,
            datatype,
            schema,
            time,
            raise_notfound=True,
            pipeline=pipeline,
            limit_mem=limit_mem,
            disable_pbar_on_first=disable_pbar_on_first,
        ):
            yield replicaset
    except KeyboardInterrupt:
        __log_interrupt()


def get_redflags(
    api_url,
    api_key,
    org_uid,
    sources,
    time,
    pipeline=None,
    limit_mem: bool = False,
    disable_pbar_on_first: bool = False,
) -> Generator[Dict, None, None]:
    try:
        if sources and sources[0].startswith("clus:"):
            datatype = lib.DATATYPE_K8S
        else:
            datatype = lib.DATATYPE_REDFLAGS
        schema = lib.EVENT_REDFLAG_PREFIX
        for redflag in retrieve_data(
            api_url,
            api_key,
            org_uid,
            sources,
            datatype,
            schema,
            time,
            pipeline=pipeline,
            limit_mem=limit_mem,
            disable_pbar_on_first=disable_pbar_on_first,
        ):
            yield redflag
    except KeyboardInterrupt:
        __log_interrupt()


def get_replicaset(
    api_url,
    api_key,
    org_uid,
    clusters,
    time,
    pipeline=None,
    limit_mem: bool = False,
    disable_pbar_on_first: bool = False,
) -> Generator[Dict, None, None]:
    try:
        datatype = lib.DATATYPE_K8S
        schema = lib.MODEL_REPLICASET_PREFIX
        for replicaset in retrieve_data(
            api_url,
            api_key,
            org_uid,
            clusters,
            datatype,
            schema,
            time,
            raise_notfound=True,
            pipeline=pipeline,
            limit_mem=limit_mem,
            disable_pbar_on_first=disable_pbar_on_first,
        ):
            yield replicaset
    except KeyboardInterrupt:
        __log_interrupt()


def get_spydertraces(
    api_url,
    api_key,
    org_uid,
    muids,
    time,
    pipeline=None,
    limit_mem: bool = False,
    disable_pbar_on_first: bool = False,
) -> Generator[Dict, None, None]:
    try:
        datatype = lib.DATATYPE_SPYDERGRAPH
        schema = lib.MODEL_SPYDERTRACE_PREFIX
        for spydertrace in retrieve_data(
            api_url,
            api_key,
            org_uid,
            muids,
            datatype,
            schema,
            time,
            pipeline=pipeline,
            limit_mem=limit_mem,
            disable_pbar_on_first=disable_pbar_on_first,
        ):
            yield spydertrace
    except KeyboardInterrupt:
        __log_interrupt()


# ----------------------------------------------------------------- #
#                Policy Workflow SQL-Based Resources                #
# ----------------------------------------------------------------- #


def delete_policy(api_url, api_key, org_uid, pol_uid):
    url = f"{api_url}/api/v1/org/{org_uid}/analyticspolicy/{pol_uid}"
    resp = delete(url, api_key)
    return resp


def get_policies(api_url, api_key, org_uid, params=None, raw_data=False):
    url = f"{api_url}/api/v1/org/{org_uid}/analyticspolicy/"
    params = {} if params is None else params
    if lib.METADATA_TYPE_FIELD in params:
        types = [params[lib.METADATA_TYPE_FIELD]]
    else:
        types = [lib.POL_TYPE_CONT, lib.POL_TYPE_SVC]
    policies = []
    for type in types:
        params[lib.METADATA_TYPE_FIELD] = type
        resp = get(url, api_key, params)
        for pol_json in resp.iter_lines():
            pol_list = json.loads(pol_json)
            if not raw_data:
                for pol in pol_list:
                    uid = pol["uid"]
                    policy = json.loads(pol["policy"])
                    policy[lib.METADATA_FIELD][lib.METADATA_UID_FIELD] = uid
                    policy[lib.METADATA_FIELD][lib.METADATA_CREATE_TIME] = pol[
                        "valid_from"
                    ]
                    policies.append(policy)
            else:
                policies.extend(pol_list)
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
    return resp


def put_policy_update(api_url, api_key, org_uid, pol_uid, data: Dict):
    url = f"{api_url}/api/v1/org/{org_uid}/analyticspolicy/{pol_uid}"
    resp = put(url, data, api_key)
    return resp


# ----------------------------------------------------------------- #
#               Policy Workflow Source-Based Resources              #
# ----------------------------------------------------------------- #


def get_audit_events(
    api_url,
    api_key,
    org_uid,
    time,
    src_uid,
    msg_type=None,
    since_id=None,
    disable_pbar: bool = False,
) -> List[Dict]:
    audit_events = []
    if msg_type:
        schema = (
            f"{lib.EVENT_AUDIT_PREFIX}:"
            f"{lib.EVENT_AUDIT_SUBTYPE_MAP[msg_type]}"
        )
    else:
        schema = lib.EVENT_AUDIT_PREFIX
    url = f"api/v1/org/{org_uid}/analyticspolicy/logs"
    for resp in threadpool_progress_bar_time_blocks(
        [src_uid],
        time,
        lambda uid, time_tup: get_filtered_data(
            api_url,
            api_key,
            org_uid,
            uid,
            "audit",
            schema,
            time_tup,
            pipeline=None,
            url=url,
        ),
        disable_pbar=disable_pbar,
    ):
        for event_json in resp.iter_lines():
            event = json.loads(event_json)
            audit_events.append(event)
    audit_events.sort(key=lambda event: event["time"])
    if since_id:
        for i, rec in enumerate(audit_events):
            if rec["id"] == since_id:
                if len(audit_events) > i + 1:
                    ind = i + 1
                    audit_events = audit_events[ind:]
                    break
                else:
                    return []
    return audit_events


def get_trace_summaries(
    api_url,
    api_key,
    org_uid,
    sources,
    time,
    pipeline=None,
    limit_mem: bool = False,
    disable_pbar_on_first: bool = False,
) -> Generator[Dict, None, None]:
    try:
        datatype = lib.DATATYPE_FINGERPRINTS
        schema = f"{lib.MODEL_FINGERPRINT_PREFIX}:{lib.POL_TYPE_TRACE}"
        for fingerprint in retrieve_data(
            api_url,
            api_key,
            org_uid,
            sources,
            datatype,
            schema,
            time,
            pipeline=pipeline,
            limit_mem=limit_mem,
            disable_pbar_on_first=disable_pbar_on_first,
        ):
            yield fingerprint
    except KeyboardInterrupt:
        __log_interrupt()


# ----------------------------------------------------------------- #
#                          Aggregation Counts                       #
# ----------------------------------------------------------------- #


def deviation_count():
    pass


# ----------------------------------------------------------------- #
#                         Alternative Outputs                       #
# ----------------------------------------------------------------- #


def get_agent_metrics(
    api_url,
    api_key,
    org_uid,
    sources,
    time,
    pipeline=None,
    limit_mem: bool = False,
    disable_pbar_on_first: bool = False,
) -> Generator[Dict, None, None]:
    try:
        datatype = lib.DATATYPE_AGENTS
        schema = lib.EVENT_METRICS_PREFIX
        for metric in retrieve_data(
            api_url,
            api_key,
            org_uid,
            sources,
            datatype,
            schema,
            time,
            pipeline=pipeline,
            limit_mem=limit_mem,
            disable_pbar_on_first=disable_pbar_on_first,
        ):
            yield metric
    except KeyboardInterrupt:
        __log_interrupt()


def get_audit_events_tail(
    api_url,
    api_key,
    org_uid,
    time,
    src_uid,
    tail: int = -1,  # -1 means all events
    msg_type=None,
    since_id: str = None,
    disable_pbar: bool = False,
) -> List[Dict]:
    audit_events = get_audit_events(
        api_url,
        api_key,
        org_uid,
        time,
        src_uid,
        msg_type,
        since_id,
        disable_pbar=disable_pbar,
    )
    if tail > 0:
        return audit_events[-tail:]
    if tail == 0:
        return []
    else:
        return audit_events


def get_latest_agent_metrics(
    api_url,
    api_key,
    org_uid,
    args: List[Tuple[str, Tuple]],  # list (source_uid, (st, et))
    pipeline=None,
):
    try:
        for resp in threadpool_progress_bar(
            args,
            lambda source, time_tup: get_filtered_data(
                api_url,
                api_key,
                org_uid,
                source,
                lib.DATATYPE_AGENTS,
                lib.EVENT_METRICS_PREFIX,
                time_tup,
                pipeline=pipeline,
            ),
            unpack_args=True,
        ):
            latest_time = 0
            for json_obj in reversed(list(resp.iter_lines())):
                metrics_record = json.loads(json_obj)
                time = metrics_record["time"]
                if time <= latest_time:
                    break
                else:
                    latest_time = time
                yield metrics_record
    except KeyboardInterrupt:
        __log_interrupt()


def get_pypi_version():
    url = "https://pypi.org/pypi/spyctl/json"
    try:
        resp = get(url, key=None, raise_notfound=True)
        version = resp.json().get("info", {}).get("version")
        if not version:
            # cli.try_log("Unable to parse latest pypi version")
            return None
        return version
    except ValueError:
        # cli.try_log("Unable to reach version API")
        pass


def get_sources_data_for_agents(api_url, api_key, org_uid) -> Dict:
    rv = {}
    url = f"{api_url}/api/v1/org/{org_uid}/source/"
    sources = get(url, api_key).json()
    for source in sources:
        source_uid = source["uid"]  # muid
        if "runtime_details" not in source:
            rv[source_uid] = {
                "uid": source["uid"],
                "cloud_region": lib.NOT_AVAILABLE,
                "cloud_type": lib.NOT_AVAILABLE,
                "last_data": source["last_data"],
            }
        else:
            rv[source_uid] = {
                "uid": source["uid"],
                "cloud_region": source["runtime_details"].get(
                    "cloud_region", lib.NOT_AVAILABLE
                ),
                "cloud_type": source["runtime_details"].get(
                    "cloud_type", lib.NOT_AVAILABLE
                ),
                "last_data": source["last_data"],
            }
    return rv


def validate_search_query(
    api_url, api_key, org_uid, schema_type: str, query: str
):
    url = f"{api_url}/api/v1/org/{org_uid}/search/validate"
    data = {
        "context_uid": lib.build_ctx(),
        "query": query,
        "schema": schema_type,
    }
    resp = post(url, data, api_key)
    resp = resp.json()
    if not resp["ok"]:
        return resp["error"]
    else:
        return ""


# ----------------------------------------------------------------- #
#                          Helper Functions                         #
# ----------------------------------------------------------------- #


def __log_interrupt():
    cli.try_log("\nRequest aborted, no partial results.. exiting.")
    exit(0)


# ----------------------------------------------------------------- #
#                          Tester Functions                         #
# ----------------------------------------------------------------- #


def api_diff(api_url, api_key, org_uid, obj, d_objs):
    url = f"{api_url}/api/v1/org/{org_uid}/spyctl/diff/"
    data = {
        "diff_objects": json.dumps(d_objs),
        "object": json.dumps(obj),
        "include_irrelevant": True,
        "content_type": "text",
    }
    resp = post(url, data, api_key)
    diff_data = resp.json()["diff_data"]
    return diff_data


def api_create_guardian_policy(
    api_url, api_key, org_uid, name, mode, data: Dict
) -> str:
    url = f"{api_url}/api/v1/org/{org_uid}/spyctl/guardianpolicy/build/"
    data = {"input_objects": json.dumps([data]), "mode": mode}
    if name:
        data["name"] = name
    resp = post(url, data, api_key)
    policy = resp.json()["policy"]
    return policy


def api_create_suppression_policy(
    api_url,
    api_key,
    org_uid,
    name,
    type,
    scope_to_users,
    object_uid,
    **selectors,
) -> str:
    url = f"{api_url}/api/v1/org/{org_uid}/spyctl/suppressionpolicy/build/"
    data = {"type": type}

    def dash(key: str) -> str:
        return key.replace("_", "-")

    processed_selectors = {dash(k): v for k, v in selectors.items()}
    if name:
        data["name"] = name
    if scope_to_users:
        data["scope_to_users"] = scope_to_users
    if object_uid:
        data["object_uid"] = object_uid
    if processed_selectors:
        data["selectors"] = processed_selectors
    print(data)
    resp = post(url, data, api_key)
    policy = resp.json()["policy"]
    return policy


def api_merge(api_url, api_key, org_uid, obj, m_objs):
    url = f"{api_url}/api/v1/org/{org_uid}/spyctl/merge/"
    data = {"merge_objects": json.dumps([m_objs]), "object": json.dumps(obj)}
    resp = post(url, data, api_key)
    merged_object = resp.json()["merged_object"]
    return merged_object


def api_validate(api_url, api_key, org_uid, data: Dict) -> str:
    url = f"{api_url}/api/v1/org/{org_uid}/spyctl/validate/"
    resp = post(url, data, api_key)
    invalid_msg = resp.json()["invalid_message"]
    return invalid_msg
