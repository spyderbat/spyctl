from typing import Dict, List, Tuple

from tabulate import tabulate

import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
import spyctl.api as api

SUMMARY_HEADERS = ["NAME", "LAST_SEEN_STATUS", "AGE", "CLUSTER"]


def namespace_summary_output(
    ctx: cfg.Context,
    clusters: List[str],
    time: Tuple[float, float],
    pipeline=None,
) -> str:
    data = []
    for namespace in api.get_namespaces(
        *ctx.get_api_data(), clusters, time, pipeline
    ):
        data.append(__namespace_data(namespace))
    data.sort(key=lambda x: (x[3], x[0]))
    return tabulate(
        data,
        headers=SUMMARY_HEADERS,
        tablefmt="simple",
    )


def __namespace_data(namespace: Dict) -> List:
    meta = namespace[lib.METADATA_FIELD]
    rv = [
        meta[lib.METADATA_NAME_FIELD],
        "Active",
        lib.calc_age(lib.to_timestamp(meta[lib.METADATA_CREATE_TIME])),
        namespace["cluster_name"] or namespace["cluster_uid"],
    ]
    return rv
