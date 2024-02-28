from typing import List, Tuple, Dict
import spyctl.api as api
import spyctl.config.configs as cfg
from tabulate import tabulate
import spyctl.spyctl_lib as lib

SUMMARY_HEADERS = ["NAME", "CREATED_AT", "STATUS", "AGE", "CLUSTER"]


def clusterrole_output_summary(
    ctx: cfg.Context,
    clusters: List[str],
    time: Tuple[float, float],
    pipeline=None,
    limit_mem=False,
) -> str:
    data = []
    for clusterrole in api.get_clusterrole(
        *ctx.get_api_data(), clusters, time, pipeline, limit_mem
    ):
        data.append(clusterrole_summary_data(clusterrole))
    rv = tabulate(
        sorted(data, key=lambda x: [x[0], x[3]]),
        headers=SUMMARY_HEADERS,
        tablefmt="plain",
    )
    return rv


def clusterrole_summary_data(clusterrole: Dict) -> List[str]:
    cluster_name = clusterrole["cluster_name"]
    meta = clusterrole[lib.METADATA_FIELD]
    name = meta["name"]
    k8s_status = clusterrole["status"]
    created_at = meta[lib.METADATA_CREATE_TIME]
    rv = [
        name,
        created_at,
        k8s_status,
        lib.calc_age(lib.to_timestamp(meta[lib.METADATA_CREATE_TIME])),
        cluster_name,
    ]
    return rv
