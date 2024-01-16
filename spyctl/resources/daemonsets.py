from typing import List, Tuple
import spyctl.api as api
import spyctl.config.configs as cfg

# import spyctl.spyctl_lib as lib
# from tabulate import tabulate


def daemonsets_output_summary(
    ctx: cfg.Context,
    clusters: List[str],
    time: Tuple[float, float],
    pipeline=None,
    limit_mem=False,
) -> str:
    data = []
    for daemonset in api.get_daemonsets(
        *ctx.get_api_data(), clusters, time, pipeline, limit_mem
    ):
        data.append(daemonset)
    return data
