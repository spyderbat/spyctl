from typing import Dict, List, Tuple
from tabulate import tabulate
import spyctl.spyctl_lib as lib
import spyctl.config.configs as cfg
import spyctl.api as api


SUMMARY_HEADERS = [
    "TRIGGER_NAME",
    "ROOT_PROCESS",
    "UNIQUE_FLAGS",
    "OBJECTS",
    "SCORE",
    "STATUS",
    "AGE",
]
WIDE_HEADERS = [
    "UID",
    "TRIGGER_NAME",
    "ROOT_PROCESS",
    "UNIQUE_FLAGS",
    "OBJECTS",
    "SCORE",
    "PROCESSES",
    "DEPTH",
    "SYSTEMS",
    "CONNECTIONS",
    "START_TIME",
]


def spydertraces_stream_summary_output(
    ctx: cfg.Context,
    muids: List[str],
    time: Tuple[float, float],
    pipeline=None,
    limit_mem=False,
) -> str:
    data = []
    for spydertrace in api.get_spydertraces(
        *ctx.get_api_data(), muids, time, pipeline, limit_mem
    ):
        data.append(spydertrace_summary_data(spydertrace))
    return tabulate(
        data,
        headers=SUMMARY_HEADERS,
        tablefmt="plain",
    )


def spydertrace_summary_data(trace: Dict) -> List:
    rv = [
        trace[lib.BE_TRIGGER_NAME],
        trace[lib.BE_ROOT_PROC_NAME],
        trace[lib.BE_UNIQUE_FLAG_COUNT],
        trace[lib.BE_OBJECT_COUNT],
        trace[lib.BE_SCORE],
        trace[lib.STATUS_FIELD],
        lib.calc_age(trace[lib.VALID_FROM_FIELD]),
    ]
    return rv


def spydertraces_stream_output_wide(
    ctx: cfg.Context,
    muids: List[str],
    time: Tuple[float, float],
    pipeline=None,
    limit_mem=False,
) -> str:
    data = []
    for spydertrace in api.get_spydertraces(
        *ctx.get_api_data(), muids, time, pipeline, limit_mem
    ):
        data.append(spydertraces_wide_data(spydertrace))
    return tabulate(
        data,
        headers=WIDE_HEADERS,
        tablefmt="simple",
    )


def spydertraces_wide_data(trace: Dict) -> List:
    rv = [
        trace[lib.ID_FIELD],
        trace[lib.BE_TRIGGER_NAME],
        trace[lib.BE_ROOT_PROC_NAME],
        trace[lib.BE_UNIQUE_FLAG_COUNT],
        trace[lib.BE_OBJECT_COUNT],
        trace[lib.BE_SCORE],
        trace[lib.BE_PROCESSES],
        trace[lib.BE_DEPTH],
        trace[lib.BE_SYSTEMS],
        trace[lib.BE_CONNECTIONS],
        lib.calc_age(trace["valid_from"]),
    ]
    return rv
