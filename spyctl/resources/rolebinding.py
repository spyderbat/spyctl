from typing import List, Tuple, Dict
import spyctl.api as api
import spyctl.config.configs as cfg
from tabulate import tabulate
import spyctl.spyctl_lib as lib

SUMMARY_HEADERS = [
    "NAME",
    "KIND/ROLE",
    "CREATED_AT",
    "STATUS",
    "AGE",
    "NAMESPACE",
    "CLUSTER",
]


def rolebinding_output_summary(
    ctx: cfg.Context,
    clusters: List[str],
    time: Tuple[float, float],
    pipeline=None,
    limit_mem=False,
) -> str:
    data = []
    for rolebinding in api.get_rolebinding(
        *ctx.get_api_data(), clusters, time, pipeline, limit_mem
    ):
        data.append(rolebinding_summary_data(rolebinding))
    rv = tabulate(
        sorted(data, key=lambda x: [x[0], x[4], x[5]]),
        headers=SUMMARY_HEADERS,
        tablefmt="plain",
    )
    return rv


def rolebinding_summary_data(rolebinding: Dict) -> List[str]:
    cluster_name = rolebinding["cluster_name"]
    meta = rolebinding[lib.METADATA_FIELD]
    name = meta["name"]
    namespace = meta["namespace"]
    k8s_status = rolebinding["status"]
    created_at = meta[lib.METADATA_CREATE_TIME]
    if "roleRef" in rolebinding:
        crb_role = rolebinding["roleRef"]["name"]
        kind = rolebinding["roleRef"]["kind"]
        role_name = kind + "/" + crb_role
    rv = [
        name,
        role_name,
        created_at,
        k8s_status,
        lib.calc_age(lib.to_timestamp(meta[lib.METADATA_CREATE_TIME])),
        namespace,
        cluster_name,
    ]
    return rv
