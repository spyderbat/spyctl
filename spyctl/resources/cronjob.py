from typing import List, Tuple, Dict
import spyctl.api as api
import spyctl.config.configs as cfg
from tabulate import tabulate
import spyctl.spyctl_lib as lib


SUMMARY_HEADERS = [
    "NAME",
    "STATUS",
    "SCHEDULE",
    "AGE",
    "NAMESPACE",
    "CLUSTER",
]

SUMMARY_HEADERS_WIDE = [
    "NAME",
    "CREATED_AT",
    "STATUS",
    "SCHEDULE",
    "SUSPEND",
    "AGE",
    "LAST_SCHEDULE",
    "NAMESPACE",
    "CLUSTER",
]


def cronjob_output_summary(
    ctx: cfg.Context,
    clusters: List[str],
    time: Tuple[float, float],
    pipeline=None,
    limit_mem=False,
) -> str:
    data = []
    for cronjob in api.get_cronjob(
        *ctx.get_api_data(), clusters, time, pipeline, limit_mem
    ):
        data.append(cronjob_summary_data(cronjob))
    rv = tabulate(
        sorted(data, key=lambda x: [x[0], x[4]]),
        headers=SUMMARY_HEADERS,
        tablefmt="plain",
    )
    return rv


def cronjob_wide_output_summary(
    ctx: cfg.Context,
    clusters: List[str],
    time: Tuple[float, float],
    pipeline=None,
    limit_mem=False,
) -> str:
    data = []
    for cronjob in api.get_cronjob(
        *ctx.get_api_data(), clusters, time, pipeline, limit_mem
    ):
        data.append(cronjob_wide_summary_data(cronjob))
    rv = tabulate(
        sorted(data, key=lambda x: [x[0], x[7]]),
        headers=SUMMARY_HEADERS_WIDE,
        tablefmt="plain",
    )
    return rv


def cronjob_summary_data(cronjob: Dict) -> List[str]:
    spec = cronjob["spec"]
    cluster_name = cronjob["cluster_name"]
    meta = cronjob[lib.METADATA_FIELD]
    name = meta["name"]
    namespace = meta["namespace"]
    status = cronjob["status"]
    # k8s_status = cronjob["k8s_status"]
    schedule = spec["schedule"]
    created_at = meta[lib.METADATA_CREATE_TIME]
    rv = [
        name,
        status,
        schedule,
        lib.calc_age(lib.to_timestamp(created_at)),
        namespace,
        cluster_name,
    ]
    return rv


def cronjob_wide_summary_data(cronjob: Dict) -> List[str]:
    spec = cronjob["spec"]
    cluster_name = cronjob["cluster_name"]
    meta = cronjob[lib.METADATA_FIELD]
    name = meta["name"]
    namespace = meta["namespace"]
    status = cronjob["status"]
    k8s_status = cronjob["k8s_status"]
    schedule = spec["schedule"]
    suspend = spec["suspend"]
    lastScheduleTime = k8s_status["lastScheduleTime"]
    created_at = meta[lib.METADATA_CREATE_TIME]
    rv = [
        name,
        created_at,
        status,
        schedule,
        suspend,
        lib.calc_age(lib.to_timestamp(created_at)),
        lib.calc_age(lib.to_timestamp(lastScheduleTime)),
        namespace,
        cluster_name,
    ]
    return rv
