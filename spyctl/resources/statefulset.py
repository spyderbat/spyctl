from typing import List, Tuple, Dict
import spyctl.api as api
import spyctl.config.configs as cfg
from tabulate import tabulate
import spyctl.spyctl_lib as lib


SUMMARY_HEADERS = [
    "NAME",
    "STATUS",
    "READY",
    "AGE",
    "NAMESPACE",
    "CLUSTER",
]

SUMMARY_HEADERS_WIDE = [
    "NAME",
    "CREATED_AT",
    "STATUS",
    "READY",
    "AGE",
    "NAMESPACE",
    "CLUSTER",
]


def statefulset_output_summary(
    ctx: cfg.Context,
    clusters: List[str],
    time: Tuple[float, float],
    pipeline=None,
    limit_mem=False,
) -> str:
    data = []
    for statefulset in api.get_statefulset(
        *ctx.get_api_data(), clusters, time, pipeline, limit_mem
    ):
        data.append(statefulset_summary_data(statefulset))
    rv = tabulate(
        sorted(data, key=lambda x: [x[0], x[4]]),
        headers=SUMMARY_HEADERS,
        tablefmt="plain",
    )
    return rv


def statefulset_wide_output_summary(
    ctx: cfg.Context,
    clusters: List[str],
    time: Tuple[float, float],
    pipeline=None,
    limit_mem=False,
) -> str:
    data = []
    for statefulset in api.get_statefulset(
        *ctx.get_api_data(), clusters, time, pipeline, limit_mem
    ):
        data.append(statefulset_wide_summary_data(statefulset))
    rv = tabulate(
        sorted(data, key=lambda x: [x[0], x[5]]),
        headers=SUMMARY_HEADERS_WIDE,
        tablefmt="plain",
    )
    return rv


def statefulset_summary_data(statefulset: Dict) -> List[str]:
    cluster_name = statefulset["cluster_name"]
    meta = statefulset[lib.METADATA_FIELD]
    name = meta["name"]
    namespace = meta["namespace"]
    status = statefulset["status"]
    k8s_status = statefulset["k8s_status"]
    available_replicas = k8s_status["availableReplicas"]
    replicas = k8s_status["replicas"]
    ready_replicas = str(available_replicas) + "/" + str(replicas)
    rv = [
        name,
        status,
        ready_replicas,
        lib.calc_age(lib.to_timestamp(meta[lib.METADATA_CREATE_TIME])),
        namespace,
        cluster_name,
    ]
    return rv


def statefulset_wide_summary_data(statefulset: Dict) -> List[str]:
    cluster_name = statefulset["cluster_name"]
    meta = statefulset[lib.METADATA_FIELD]
    name = meta["name"]
    namespace = meta["namespace"]
    status = statefulset["status"]
    k8s_status = statefulset["k8s_status"]
    available_replicas = k8s_status["availableReplicas"]
    replicas = k8s_status["replicas"]
    ready_replicas = str(available_replicas) + "/" + str(replicas)
    created_at = meta[lib.METADATA_CREATE_TIME]
    rv = [
        name,
        created_at,
        status,
        ready_replicas,
        lib.calc_age(lib.to_timestamp(meta[lib.METADATA_CREATE_TIME])),
        namespace,
        cluster_name,
    ]
    return rv
