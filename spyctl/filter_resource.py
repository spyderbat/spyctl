import fnmatch
import time
from typing import Dict, List, Union, Optional, Iterable

import spyctl.api as api
import spyctl.config.configs as cfgs
import spyctl.spyctl_lib as lib

DEFAULT_FILTER_TIME = (lib.time_inp("2h"), time.time())

CLUSTERS_TGT_FIELDS = ["uid", "name"]
MACHINES_TGT_FIELDS = ["uid", "name"]
CONT_SEL_TGT = f"{lib.SPEC_FIELD}.{lib.CONT_SELECTOR_FIELD}"
SVC_SEL_TGT = f"{lib.SPEC_FIELD}.{lib.SVC_SELECTOR_FIELD}"
CGROUP_TGT_FIELDS = [f"{SVC_SEL_TGT}.{lib.CGROUP_FIELD}"]
CONT_NAME_TGT_FIELDS = [f"{CONT_SEL_TGT}.{lib.CONT_NAME_FIELD}"]
CONT_ID_TGT_FIELDS = [f"{CONT_SEL_TGT}.{lib.CONT_ID_FIELD}"]
IMAGE_TGT_FIELDS = [f"{CONT_SEL_TGT}.{lib.IMAGE_FIELD}"]
IMAGEID_TGT_FIELDS = [f"{CONT_SEL_TGT}.{lib.IMAGEID_FIELD}"]


def filter_clusters(
    clusters_data: List[Dict],
    namespaces_data=None,
    machines_data=None,
    pods_data=None,
    cgroups_data=None,
    containers_data=None,
    **filters,
):
    def namespace_filter(data, filt):
        if namespaces_data is None:
            ctx = cfgs.get_current_context()
            namespaces = api.get_namespaces(
                *ctx.get_api_data(),
                data,
                DEFAULT_FILTER_TIME,
            )
            namespaces = filter_obj(namespaces, ["namespaces"], filt)
            cluster_uids = [ns["cluster_uid"] for ns in namespaces]
            return filter_obj(data, ["uid"], cluster_uids)

    filter_set = {
        cfgs.CLUSTER_FIELD: lambda data, filt: filter_obj(
            data, CLUSTERS_TGT_FIELDS, filt
        ),
        cfgs.NAMESPACE_FIELD: namespace_filter,
    }
    clusters_data = use_filters(clusters_data, filter_set, filters)
    return clusters_data


def filter_namespaces(
    namespaces_data: List[Dict],
    clusters_data=None,
    machines_data=None,
    pods_data=None,
    cgroups_data=None,
    containers_data=None,
    **filters,
):
    filter_set = {
        cfgs.CLUSTER_FIELD: lambda data, filt: filter_obj(
            data, ["cluster_uid", "cluster_name"], filt
        ),
    }
    namespaces_data = use_filters(namespaces_data, filter_set, filters)
    return namespaces_data


def filter_machines(
    machines_data: List[Dict],
    clusters_data=None,
    namespaces_data=None,
    pods_data=None,
    cgroups_data=None,
    containers_data=None,
    **filters,
):
    filter_set = {
        cfgs.MACHINES_FIELD: lambda data, filt: filter_obj(
            data, MACHINES_TGT_FIELDS, filt
        ),
    }
    machines_data = use_filters(machines_data, filter_set, filters)
    return machines_data


def filter_nodes(
    nodes_data: List[Dict],
    clusters_data=None,
    namespaces_data=None,
    pods_data=None,
    cgroups_data=None,
    containers_data=None,
    **filters,
):
    filter_set = {
        cfgs.MACHINES_FIELD: lambda data, filt: filter_obj(
            data, ["muid"], filt
        ),
    }
    nodes_data = use_filters(nodes_data, filter_set, filters)
    return nodes_data


def filter_fingerprints(
    fingerprint_data: List[Dict],
    namespaces_data=None,
    clusters_data=None,
    machines_data=None,
    pods_data=None,
    cgroups_data=None,
    containers_data=None,
    **filters,
):
    def cont_id_filter(data, filt):
        filt += "*" if filt[-1] != "*" else filt
        return filter_obj(data, CONT_ID_TGT_FIELDS, filt)

    def image_id_filter(data, filt):
        filt += "*" if filt[-1] != "*" else filt
        return filter_obj(data, IMAGEID_TGT_FIELDS, filt)

    filter_set = {
        cfgs.CGROUP_FIELD: lambda data, filt: filter_obj(
            data, CGROUP_TGT_FIELDS, filt
        ),
        lib.CONT_NAME_FIELD: lambda data, filt: filter_obj(
            data, CONT_NAME_TGT_FIELDS, filt
        ),
        lib.CONT_ID_FIELD: cont_id_filter,
        lib.IMAGE_FIELD: lambda data, filt: filter_obj(
            data, CGROUP_TGT_FIELDS, filt
        ),
        lib.IMAGEID_FIELD: image_id_filter,
    }
    fingerprint_data = use_filters(fingerprint_data, filter_set, filters)
    return fingerprint_data


def filter_fprint_groups(
    fprint_grp_data: List[Dict],
    namespaces_data=None,
    clusters_data=None,
    machines_data=None,
    pods_data=None,
    cgroups_data=None,
    containers_data=None,
    **filters,
):
    return fprint_grp_data


def filter_policies(
    policy_data: List[Dict],
    namespaces_data=None,
    clusters_data=None,
    machines_data=None,
    pods_data=None,
    cgroups_data=None,
    containers_data=None,
    **filters,
):
    return policy_data


def filter_pods(
    pods_data: List[Dict],
    namespaces_data=None,
    clusters_data=None,
    machines_data=None,
    cgroups_data=None,
    containers_data=None,
    **filters,
):
    filter_set = {
        cfgs.NAMESPACE_FIELD: lambda data, filt: filter_obj(
            data, [f"{lib.METADATA_FIELD}.namespace"], filt
        ),
    }
    pods_data = use_filters(pods_data, filter_set, filters)
    return pods_data


def use_filters(data, filter_functions: Dict, filters: Dict):
    ctx_filters = cfgs.get_current_context().get_filters()
    for filt, func in filter_functions.items():
        if filt in filters:
            data = func(data, filters[filt])
        elif filt in ctx_filters:
            data = func(data, ctx_filters[filt])
    return data


def filter_obj(
    obj: List[Dict], target_fields: List[str], filters: Union[List[str], str]
) -> List[Dict]:
    rv = []
    if "-all" in filters:
        return obj
    if isinstance(filters, list):
        for rec in obj:
            if match_filters(rec, target_fields, filters):
                rv.append(rec)
    else:
        for rec in obj:
            if match_filters(rec, target_fields, [filters]):
                rv.append(rec)
    return rv


def match_filters(
    record: Dict, target_fields: List[str], filters: List[str]
) -> bool:
    for fil in filters:
        for field in target_fields:
            value = get_field_value(field, record)
            if value is None:
                continue
            if "*" in fil:
                if isinstance(value, str) and fnmatch.fnmatch(value, fil):
                    return True
                try:
                    if not isinstance(value, str):
                        for val in get_field_value(field, record):
                            if fnmatch.fnmatch(val, fil):
                                return True
                except Exception:
                    pass
            else:
                if value == fil:
                    return True
                try:
                    if fil in get_field_value(
                        field, record
                    ) and not isinstance(value, str):
                        return True
                except Exception:
                    pass
    return False


def get_field_value(field: str, obj: Dict) -> Optional[Union[str, Iterable]]:
    keys = field.split(".")
    value = obj
    for key in keys:
        value = value.get(key)
        if value is None:
            return None
    return value
