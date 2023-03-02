import fnmatch
import time
from copy import deepcopy
from typing import Dict, Iterable, List, Optional, Union

import spyctl.api as api
import spyctl.config.configs as cfgs
import spyctl.spyctl_lib as lib

DEFAULT_FILTER_TIME = (lib.time_inp("2h"), time.time())

CONT_SEL_TGT = [lib.SPEC_FIELD, lib.CONT_SELECTOR_FIELD]
SVC_SEL_TGT = [lib.SPEC_FIELD, lib.SVC_SELECTOR_FIELD]
NS_SEL_TGT = [
    lib.SPEC_FIELD,
    lib.NAMESPACE_SELECTOR_FIELD,
    lib.MATCH_LABELS_FIELD,
]
POD_SEL_TGT = [lib.SPEC_FIELD, lib.POD_SELECTOR_FIELD, lib.MATCH_LABELS_FIELD]
CLUSTERS_TGT_FIELDS = ["uid", "name"]
MACHINES_TGT_FIELDS = ["uid", "name"]
CGROUP_TGT_FIELDS = [[*SVC_SEL_TGT, lib.CGROUP_FIELD]]
CONT_NAME_TGT_FIELDS = [*CONT_SEL_TGT, lib.CONT_NAME_FIELD]
CONT_ID_TGT_FIELDS = [[*CONT_SEL_TGT, lib.CONT_ID_FIELD]]
IMAGE_TGT_FIELDS = [[*CONT_SEL_TGT, lib.IMAGE_FIELD]]
IMAGEID_TGT_FIELDS = [[*CONT_SEL_TGT, lib.IMAGEID_FIELD]]
NAMESPACE_LABEL_TGT_FIELDS = [[*NS_SEL_TGT]]
POD_LABEL_TGT_FIELDS = [[*POD_SEL_TGT]]


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
    use_context_filters=True,
    **filters,
):
    filter_set = {
        cfgs.MACHINES_FIELD: lambda data, filt: filter_obj(
            data, MACHINES_TGT_FIELDS, filt
        ),
    }
    machines_data = use_filters(
        machines_data, filter_set, filters, use_context_filters
    )
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


def filter_redflags(
    flag_grp_data: List[Dict],
    namespaces_data=None,
    clusters_data=None,
    machines_data=None,
    pods_data=None,
    cgroups_data=None,
    containers_data=None,
    **filters,
):
    def severity_filter(data, filt):
        index = -1
        try:
            index = lib.ALLOWED_SEVERITIES.index(filt)
        except ValueError:
            return data
        rv = []
        for flag in data:
            try:
                if lib.ALLOWED_SEVERITIES.index(flag["severity"]) <= index:
                    rv.append(flag)
            except ValueError:
                rv.append(flag)
        return rv

    def exceptions_filter(data, filt):
        if filt:
            return data
        return [flag for flag in data if not flag["false_positive"]]

    filter_set = {
        cfgs.MACHINES_FIELD: lambda data, filt: filter_obj(
            data, ["muid"], filt
        ),
        lib.FLAG_SEVERITY: severity_filter,
        "exceptions": exceptions_filter,
    }
    flag_grp_data = use_filters(flag_grp_data, filter_set, filters)
    return flag_grp_data


def filter_opsflags(
    flag_grp_data: List[Dict],
    namespaces_data=None,
    clusters_data=None,
    machines_data=None,
    pods_data=None,
    cgroups_data=None,
    containers_data=None,
    **filters,
):
    def severity_filter(data, filt):
        index = -1
        try:
            index = lib.ALLOWED_SEVERITIES.index(filt)
        except ValueError:
            return data
        rv = []
        for flag in data:
            try:
                if lib.ALLOWED_SEVERITIES.index(flag["severity"]) <= index:
                    rv.append(flag)
            except ValueError:
                rv.append(flag)
        return rv

    filter_set = {
        cfgs.MACHINES_FIELD: lambda data, filt: filter_obj(
            data, ["muid"], filt
        ),
        lib.FLAG_SEVERITY: severity_filter,
    }
    flag_grp_data = use_filters(flag_grp_data, filter_set, filters)
    return flag_grp_data


def filter_fingerprints(
    fingerprint_data: List[Dict],
    namespaces_data=None,
    clusters_data=None,
    machines_data=None,
    pods_data=None,
    cgroups_data=None,
    containers_data=None,
    use_context_filters=True,
    **filters,
):
    def cont_id_filter(data, filt):
        filt += "*" if filt[-1] != "*" else filt
        return filter_obj(data, CONT_ID_TGT_FIELDS, filt)

    def image_id_filter(data, filt):
        filt += "*" if filt[-1] != "*" else filt
        return filter_obj(data, IMAGEID_TGT_FIELDS, filt)

    def filter_namespace_labels(data, filt: Dict):
        for key, value in filt.items():
            tgt_fields = deepcopy(NAMESPACE_LABEL_TGT_FIELDS)
            tgt_fields[0].append(key)
            data = filter_obj(
                data,
                tgt_fields,
                value,
            )
        return data

    def filter_pod_labels(data, filt: Dict):
        for key, value in filt.items():
            tgt_fields = deepcopy(POD_LABEL_TGT_FIELDS)
            tgt_fields[0].append(key)
            data = filter_obj(
                data,
                tgt_fields,
                value,
            )
        return data

    filter_set = {
        cfgs.CGROUP_FIELD: lambda data, filt: filter_obj(
            data, CGROUP_TGT_FIELDS, filt
        ),
        lib.CONT_NAME_FIELD: lambda data, filt: filter_obj(
            data, CONT_NAME_TGT_FIELDS, filt
        ),
        lib.CONT_ID_FIELD: cont_id_filter,
        lib.IMAGE_FIELD: lambda data, filt: filter_obj(
            data, IMAGE_TGT_FIELDS, filt
        ),
        lib.IMAGEID_FIELD: image_id_filter,
        lib.NAMESPACE_FIELD: lambda data, filt: filter_obj(
            data,
            [[lib.METADATA_FIELD, lib.METADATA_NAMESPACE_FIELD]],
            filt,
        ),
        lib.NAMESPACE_LABELS_FIELD: filter_namespace_labels,
        lib.POD_LABELS_FIELD: filter_pod_labels,
    }
    fingerprint_data = use_filters(
        fingerprint_data, filter_set, filters, use_context_filters
    )
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
            data, [[lib.METADATA_FIELD, lib.METADATA_NAMESPACE_FIELD]], filt
        ),
    }
    pods_data = use_filters(pods_data, filter_set, filters)
    return pods_data


def filter_processes(
    processes: List[Dict],
    namespaces_data=None,
    clusters_data=None,
    machines_data=None,
    pods_data=None,
    cgroups_data=None,
    containers_data=None,
    **filters,
):
    return processes


def filter_connections(
    connections: List[Dict],
    namespaces_data=None,
    clusters_data=None,
    machines_data=None,
    pods_data=None,
    cgroups_data=None,
    containers_data=None,
    **filters,
):
    return connections


def use_filters(
    data, filter_functions: Dict, filters: Dict, use_context_filters=True
):
    ctx_filters = cfgs.get_current_context().get_filters()
    data_empty_at_start = len(data) == 0
    for filt, func in filter_functions.items():
        if filt in filters:
            data = func(data, filters[filt])
        elif use_context_filters and filt in ctx_filters:
            data = func(data, ctx_filters[filt])
        if len(data) == 0 and not data_empty_at_start:
            lib.try_log(f"No results after filtering on {filt}")
            return data
    return data


def filter_obj(
    obj: List[Dict],
    target_fields: List[Union[str, List[str]]],
    filters: Union[List[str], str],
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


def get_field_value(
    field: Union[str, List[str]], obj: Dict
) -> Optional[Union[str, Iterable]]:
    value = obj
    if isinstance(field, str):
        key = field
        value = value.get(key)
        if value is None:
            return None
    else:
        keys = field
        for key in keys:
            value = value.get(key)
            if value is None:
                return None
    return value
