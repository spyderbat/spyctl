from typing import List, Tuple

# from tabulate import tabulate

import spyctl.api as api
import spyctl.config.configs as cfg

# import spyctl.spyctl_lib as lib


def replicaset_output_summary(
    ctx: cfg.Context,
    clusters: List[str],
    time: Tuple[float, float],
    pipeline=None,
    limit_mem=False,
) -> str:
    data = []
    for replicaset in api.get_replicaset(
        *ctx.get_api_data(), clusters, time, pipeline, limit_mem
    ):
        data.append(replicaset)
    # print("i'm data", data)
    return data
