from typing import Dict, List, Tuple

from tabulate import tabulate

import spyctl.api as api
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib

SUMMARY_HEADERS = [
    "NAME",
    "SPYDERBAT_STATUS",
    "AGE",
    "VERSION",
    "CLUSTER",
    "MUID",
]


def nodes_output_summary(
    ctx: cfg.Context,
    clusters: List[str],
    time: Tuple[float, float],
    pipeline=None,
    limit_mem=False,
) -> str:
    data = []
    for node in api.get_nodes(
        *ctx.get_api_data(), clusters, time, pipeline, limit_mem
    ):
        data.append(__node_summary_data(node))
    rv = tabulate(
        sorted(data, key=lambda x: [x[4], x[1], x[2], x[0]]),
        headers=SUMMARY_HEADERS,
        tablefmt="plain",
    )
    return rv


def __node_summary_data(node: Dict) -> List[str]:
    k8s_status = node[lib.BE_K8S_STATUS]
    node_info = k8s_status[lib.NODE_INFO_FIELD]
    version = node_info.get(lib.KUBELET_VERSION_FIELD, lib.NOT_AVAILABLE)
    cluster = node.get("cluster_name") or node.get("cluster_uid")
    meta = node[lib.METADATA_FIELD]
    rv = [
        meta[lib.METADATA_NAME_FIELD],
        node["status"],
        lib.calc_age(lib.to_timestamp(meta[lib.METADATA_CREATE_TIME])),
        version,
        cluster,
        node.get("muid", lib.NOT_AVAILABLE),
    ]
    return rv
