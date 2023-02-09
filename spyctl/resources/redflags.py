from typing import Dict, List

from tabulate import tabulate

import spyctl.spyctl_lib as lib
import zulu

NOT_AVAILABLE = lib.NOT_AVAILABLE


class RedflagsGroup:
    def __init__(self) -> None:
        self.redflags = {}
        self.latest_timestamp = NOT_AVAILABLE
        self.machines = set()
    
    def add_redflag(self, flag: Dict):
        machine_uid = flag.get("muid")
        if machine_uid:
            self.machines.add(machine_uid)
        self.__update_latest_timestamp(flag.get("time"))
        self.redflags[flag['id']] = flag

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
        flag = next(iter(self.redflags.values()))
        timestamp = NOT_AVAILABLE
        if (
            self.latest_timestamp is not None
            and self.latest_timestamp != NOT_AVAILABLE
        ):
            timestamp = str(zulu.Zulu.fromtimestamp(self.latest_timestamp).format("YYYY-MM-ddTHH:mm:ss"))
        ref_obj = flag["class"][1]
        if ref_obj == "proc":
            ref_obj = "process"
        if ref_obj == "conn":
            ref_obj = "connection"
        rv = [
            flag["short_name"],
            flag["severity"],
            str(len(self.redflags)),
            timestamp,
            ref_obj,
        ]
        return rv


def redflags_output_summary(flags: List[Dict]) -> str:
    headers = [
        "FLAG",
        "SEVERITY",
        "COUNT",
        "LATEST_TIMESTAMP",
        "REF_OBJ",
    ]
    groups = {}
    for flag in flags:
        flag_class = "/".join(flag["class"])
        if flag_class in groups:
            groups[flag_class].add_redflag(flag)
        else:
            groups[flag_class] = RedflagsGroup()
    data = []
    for group in groups.values():
        data.append(group.summary_data())
    output = tabulate(
        sorted(data, key=lambda x: [_severity_index(x[1]), x[0], _to_timestamp(x[3])]),
        headers=headers,
        tablefmt="plain",
    )
    return output + "\n"


def _severity_index(severity):
    try:
        return lib.ALLOWED_SEVERITIES.index(severity)
    except ValueError:
        return -1 


def _to_timestamp(zulu_str):
    return zulu.Zulu.parse(zulu_str).timestamp()


def redflags_output(flags: List[Dict]) -> Dict:
    if len(flags) == 1:
        return flags[0]
    elif len(flags) > 1:
        return {
            lib.API_FIELD: lib.API_VERSION,
            lib.ITEMS_FIELD: flags,
        }
    else:
        return {}
