from typing import Dict, List, Tuple

from tabulate import tabulate

import spyctl.api as api
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib

SUMMARY_HEADERs = [
    "NAME",
    "READY",
    "LAST_STATUS_SEEN",
    "LAST_SEEN",
    "RESTARTS",
    "AGE",
    "NAMESPACE",
    "CLUSTER",
]


def pods_output_summary(
    ctx: cfg.Context,
    clusters: List[str],
    time: Tuple[float, float],
    pipeline=None,
    limit_mem=False,
) -> str:
    data = []
    for pod in api.get_pods(
        *ctx.get_api_data(), clusters, time, pipeline, limit_mem
    ):
        data.append(__pod_summary_data(pod))
    output = tabulate(
        sorted(data, key=lambda x: [x[7], x[6], x[0]]),
        headers=SUMMARY_HEADERs,
        tablefmt="plain",
    )
    return output


def __pod_summary_data(pod: Dict) -> List:
    k8s_status = pod[lib.BE_K8S_STATUS]
    container_statuses = k8s_status.get(lib.CONTAINER_STATUSES_FIELD, {})
    ready = __get_ready_count(container_statuses)
    restarts = __calc_restarts(container_statuses)
    meta = pod[lib.METADATA_FIELD]
    rv = [
        meta[lib.METADATA_NAME_FIELD],
        ready,
        k8s_status[lib.BE_PHASE],
        lib.epoch_to_zulu(pod["time"]),
        restarts,
        lib.calc_age(lib.to_timestamp(meta[lib.METADATA_CREATE_TIME])),
        meta[lib.NAMESPACE_FIELD],
        pod.get("cluster_name") or pod.get("cluster_uid"),
    ]
    return rv


def __get_ready_count(container_statuses: Dict):
    count = 0
    ready_count = 0
    for cont in container_statuses:
        count += 1
        if cont.get("ready", False):
            ready_count += 1
    return f"{ready_count}/{count}"


def __calc_restarts(container_statuses: Dict):
    count = 0
    for cont in container_statuses:
        count += cont.get("restartCount", 0)
    return count
