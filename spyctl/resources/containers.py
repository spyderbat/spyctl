from typing import Dict, List, Tuple

from tabulate import tabulate

import spyctl.api as api
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib

SUMMARY_HEADERS = ["IMAGE", "IMAGE_ID", "STATUS", "AGE"]


def container_output(cont: List[Dict]) -> Dict:
    if len(cont) == 1:
        return cont[0]
    elif len(cont) > 1:
        return {
            lib.API_FIELD: lib.API_VERSION,
            lib.ITEMS_FIELD: cont,
        }
    else:
        return {}


def cont_stream_summary_output(
    ctx: cfg.Context,
    muids: List[str],
    time: Tuple[float, float],
    pipeline=None,
    limit_mem=False,
):
    data = []
    for container in api.get_containers(
        *ctx.get_api_data(),
        muids,
        time,
        pipeline=pipeline,
        limit_mem=limit_mem,
    ):
        data.append(cont_summary_data(container))
    data.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    rv = tabulate(
        data,
        headers=SUMMARY_HEADERS,
        tablefmt="simple",
    )
    return rv


def cont_summary_data(container: Dict) -> List[str]:
    return [
        container[lib.BE_CONTAINER_IMAGE],
        container[lib.BE_CONTAINER_IMAGE_ID],
        container[lib.STATUS_FIELD],
        lib.calc_age(container[lib.VALID_FROM_FIELD]),
    ]
