from typing import Dict, List, Tuple

from tabulate import tabulate

import spyctl.api as api
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib

NOT_AVAILABLE = lib.NOT_AVAILABLE
SUMMARY_HEADERS = [
    "FLAG",
    "SEVERITY",
    "COUNT",
    "LATEST_TIMESTAMP",
    "REF_OBJ",
]


class FlagsGroup:
    def __init__(self) -> None:
        self.ref_flag = None
        self.latest_timestamp = NOT_AVAILABLE
        self.count = 0

    def add_flag(self, flag: Dict):
        if self.ref_flag is None:
            self.ref_flag = flag
        self.__update_latest_timestamp(flag.get("time"))
        self.count += 1

    def __update_latest_timestamp(self, timestamp):
        if timestamp is None:
            return
        if (
            self.latest_timestamp is None
            or self.latest_timestamp == NOT_AVAILABLE
        ):
            self.latest_timestamp = timestamp
        elif timestamp > self.latest_timestamp:
            self.latest_timestamp = timestamp

    def summary_data(self) -> List[str]:
        timestamp = NOT_AVAILABLE
        if (
            self.latest_timestamp is not None
            and self.latest_timestamp != NOT_AVAILABLE
        ):
            timestamp = lib.epoch_to_zulu(self.latest_timestamp)
        ref_obj = self.ref_flag["class"][1]
        if ref_obj in lib.CLASS_LONG_NAMES:
            ref_obj = lib.CLASS_LONG_NAMES[ref_obj]
        rv = [
            self.ref_flag["short_name"],
            self.ref_flag["severity"],
            str(self.count),
            timestamp,
            ref_obj,
        ]
        return rv


def flags_output_summary(
    ctx: cfg.Context,
    flag_type: str,
    muids: List[str],
    time: Tuple[float, float],
    pipeline=None,
    limit_mem=False,
) -> str:
    groups: Dict[str, FlagsGroup] = {}
    if flag_type == lib.EVENT_OPSFLAG_PREFIX:
        api_func = api.get_opsflags
    else:
        api_func = api.get_redflags
    for flag in api_func(
        *ctx.get_api_data(), muids, time, pipeline, limit_mem
    ):
        flag_class = "/".join(flag["class"])
        if flag_class not in groups:
            groups[flag_class] = FlagsGroup()
        groups[flag_class].add_flag(flag)
    data = []
    for group in groups.values():
        data.append(group.summary_data())
    output = tabulate(
        sorted(
            data,
            key=lambda x: [
                _severity_index(x[1]),
                x[0],
                x[4],
                lib.to_timestamp(x[3]),
            ],
        ),
        headers=SUMMARY_HEADERS,
        tablefmt="plain",
    )
    return output


def _severity_index(severity):
    try:
        return lib.ALLOWED_SEVERITIES.index(severity)
    except ValueError:
        return -1
