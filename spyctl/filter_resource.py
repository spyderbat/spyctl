import fnmatch
import time
from typing import Dict, List, Union, Optional, Iterable

import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfgs
import spyctl.spyctl_lib as lib

DEFAULT_FILTER_TIME = (lib.time_inp("2h"), time.time())

CLUSTERS_TGT_FIELDS = ["uid", "name"]
MACHINES_TGT_FIELDS = ["uid", "name"]


def filter_clusters(
    clusters_data: List[Dict],
    namespaces_data=None,
    machines_data=None,
    pods_data=None,
    cgroups_data=None,
    containers_data=None,
    **filters,
):
    ctx = cfgs.get_current_context()
    ctx_filters = ctx.get_filters()
    if cfgs.CLUSTER_FIELD in filters:
        clusters_data = filter_obj(
            clusters_data, CLUSTERS_TGT_FIELDS, filters[cfgs.CLUSTER_FIELD]
        )
    elif cfgs.CLUSTER_FIELD in ctx_filters:
        clusters_data = filter_obj(
            clusters_data,
            CLUSTERS_TGT_FIELDS,
            [ctx_filters[cfgs.CLUSTER_FIELD]],
        )
    if cfgs.NAMESPACE_FIELD in filters:
        if namespaces_data is None:
            namespaces = api.get_namespaces(
                *ctx.get_api_data(),
                clusters_data,
                DEFAULT_FILTER_TIME,
                cli.api_err_exit,
            )
            namespaces = filter_obj(
                namespaces, ["namespaces"], filters[cfgs.NAMESPACE_FIELD]
            )
            cluster_uids = [ns["cluster_uid"] for ns in namespaces]
            clusters_data = filter_obj(clusters_data, ["uid"], cluster_uids)
    elif cfgs.NAMESPACE_FIELD in ctx_filters:
        if namespaces_data is None:
            namespaces = api.get_namespaces(
                *ctx.get_api_data(),
                clusters_data,
                DEFAULT_FILTER_TIME,
                cli.api_err_exit,
            )
            namespaces = filter_obj(
                namespaces, ["namespaces"], ctx_filters[cfgs.NAMESPACE_FIELD]
            )
            cluster_uids = [ns["cluster_uid"] for ns in namespaces]
            clusters_data = filter_obj(clusters_data, ["uid"], cluster_uids)
    if cfgs.MACHINES_FIELD in filters:
        pass
    elif cfgs.MACHINES_FIELD in ctx_filters:
        pass
    if cfgs.POD_FIELD in filters:
        pass
    elif cfgs.POD_FIELD in ctx_filters:
        pass
    if cfgs.CGROUP_FIELD in filters:
        pass
    elif cfgs.CGROUP_FIELD in ctx_filters:
        pass
    if cfgs.CONTAINER_NAME_FIELD in filters:
        pass
    elif cfgs.CONTAINER_NAME_FIELD in ctx_filters:
        pass
    if cfgs.IMG_FIELD in filters:
        pass
    elif cfgs.IMGID_FIELD in ctx_filters:
        pass
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
    ctx = cfgs.get_current_context()
    ctx_filters = cfgs.get_current_context().get_filters()
    if cfgs.CLUSTER_FIELD in filters:
        namespaces_data = filter_obj(
            namespaces_data,
            ["cluster_uid", "cluster_name"],
            filters[cfgs.CLUSTER_FIELD],
        )
    elif cfgs.CLUSTER_FIELD in ctx_filters:
        namespaces_data = filter_obj(
            namespaces_data,
            ["cluster_uid", "cluster_name"],
            ctx_filters[cfgs.CLUSTER_FIELD],
        )
    if cfgs.NAMESPACE_FIELD in filters:
        pass
    elif cfgs.NAMESPACE_FIELD in ctx_filters:
        pass
    if cfgs.MACHINES_FIELD in filters:
        pass
    elif cfgs.MACHINES_FIELD in ctx_filters:
        pass
    if cfgs.POD_FIELD in filters:
        pass
    elif cfgs.POD_FIELD in ctx_filters:
        pass
    if cfgs.CGROUP_FIELD in filters:
        pass
    elif cfgs.CGROUP_FIELD in ctx_filters:
        pass
    if cfgs.CONTAINER_NAME_FIELD in filters:
        pass
    elif cfgs.CONTAINER_NAME_FIELD in ctx_filters:
        pass
    if cfgs.IMG_FIELD in filters:
        pass
    elif cfgs.IMGID_FIELD in ctx_filters:
        pass
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
    ctx_filters = cfgs.get_current_context().get_filters()
    if cfgs.CLUSTER_FIELD in filters:
        pass
    elif cfgs.CLUSTER_FIELD in ctx_filters:
        pass
    if cfgs.NAMESPACE_FIELD in filters:
        pass
    elif cfgs.NAMESPACE_FIELD in ctx_filters:
        pass
    if cfgs.MACHINES_FIELD in filters:
        machines_data = filter_obj(
            machines_data, MACHINES_TGT_FIELDS, filters[cfgs.MACHINES_FIELD]
        )
    elif cfgs.MACHINES_FIELD in ctx_filters:
        machines_data = filter_obj(
            machines_data,
            MACHINES_TGT_FIELDS,
            ctx_filters[cfgs.MACHINES_FIELD],
        )
    if cfgs.POD_FIELD in filters:
        pass
    elif cfgs.POD_FIELD in ctx_filters:
        pass
    if cfgs.CGROUP_FIELD in filters:
        pass
    elif cfgs.CGROUP_FIELD in ctx_filters:
        pass
    if cfgs.CONTAINER_NAME_FIELD in filters:
        pass
    elif cfgs.CONTAINER_NAME_FIELD in ctx_filters:
        pass
    if cfgs.IMG_FIELD in filters:
        pass
    elif cfgs.IMGID_FIELD in ctx_filters:
        pass
    return machines_data


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
    ctx_filters = cfgs.get_current_context().get_filters()
    if cfgs.CLUSTER_FIELD in filters:
        pass
    elif cfgs.CLUSTER_FIELD in ctx_filters:
        pass
    if cfgs.NAMESPACE_FIELD in filters:
        pass
    elif cfgs.NAMESPACE_FIELD in ctx_filters:
        pass
    if cfgs.MACHINES_FIELD in filters:
        pass
    elif cfgs.MACHINES_FIELD in ctx_filters:
        pass
    if cfgs.POD_FIELD in filters:
        pass
    elif cfgs.POD_FIELD in ctx_filters:
        pass
    if cfgs.CGROUP_FIELD in filters:
        pass
    elif cfgs.CGROUP_FIELD in ctx_filters:
        pass
    if cfgs.CONTAINER_NAME_FIELD in filters:
        pass
    elif cfgs.CONTAINER_NAME_FIELD in ctx_filters:
        pass
    if cfgs.IMG_FIELD in filters:
        pass
    elif cfgs.IMGID_FIELD in ctx_filters:
        pass
    return fingerprint_data


def filter_pods(
    pods_data: List[Dict],
    namespaces_data=None,
    clusters_data=None,
    machines_data=None,
    cgroups_data=None,
    containers_data=None,
    **filters,
):
    ctx_filters = cfgs.get_current_context().get_filters()
    if cfgs.CLUSTER_FIELD in filters:
        pass
    elif cfgs.CLUSTER_FIELD in ctx_filters:
        pass
    if cfgs.NAMESPACE_FIELD in filters:
        pods_data = filter_obj(
            pods_data,
            [f"{lib.METADATA_FIELD}.namespace"],
            filters[cfgs.NAMESPACE_FIELD],
        )
    elif cfgs.NAMESPACE_FIELD in ctx_filters:
        pods_data = filter_obj(
            pods_data,
            [f"{lib.METADATA_FIELD}.namespace"],
            ctx_filters[cfgs.NAMESPACE_FIELD],
        )
    if cfgs.MACHINES_FIELD in filters:
        pass
    elif cfgs.MACHINES_FIELD in ctx_filters:
        pass
    if cfgs.POD_FIELD in filters:
        pass
    elif cfgs.POD_FIELD in ctx_filters:
        pass
    if cfgs.CGROUP_FIELD in filters:
        pass
    elif cfgs.CGROUP_FIELD in ctx_filters:
        pass
    if cfgs.CONTAINER_NAME_FIELD in filters:
        pass
    elif cfgs.CONTAINER_NAME_FIELD in ctx_filters:
        pass
    if cfgs.IMG_FIELD in filters:
        pass
    elif cfgs.IMGID_FIELD in ctx_filters:
        pass
    return pods_data


def filter_obj(
    obj: List[Dict], target_fields: str, filters: Union[List[str], str]
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
            if "*" in fil:
                if fnmatch.fnmatch(get_field_value(field, record), fil):
                    return True
                try:
                    if not isinstance(get_field_value(field, record), str):
                        for val in get_field_value(field, record):
                            if fnmatch.fnmatch(val, fil):
                                return True
                except Exception:
                    pass
            else:
                if get_field_value(field, record) == fil:
                    return True
                try:
                    if fil in get_field_value(
                        field, record
                    ) and not isinstance(get_field_value(field, record), str):
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
