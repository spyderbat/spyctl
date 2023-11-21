from typing import Dict, List, Tuple

import zulu
from tabulate import tabulate

import spyctl.api as api
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib

NOT_AVAILABLE = lib.NOT_AVAILABLE
SUMMARY_HEADERS = [
    "NAME",
    "EXE",
    "ROOT_EXECUTION",
    "COUNT",
    "LATEST_EXECUTED",
]


class ProcessGroup:
    def __init__(self, multiple_exes) -> None:
        self.ref_proc = None
        self.latest_timestamp = NOT_AVAILABLE
        self.count = 0
        self.root = False
        self.multiple_exes = multiple_exes

    def add_proc(self, proc: Dict):
        self.__update_latest_timestamp(proc.get("create_time"))
        if self.ref_proc is None:
            self.ref_proc = proc
        if proc.get("euid") == 0:
            self.root = True
        self.count += 1

    def __update_latest_timestamp(self, timestamp):
        if timestamp is None:
            return
        if self.latest_timestamp == NOT_AVAILABLE:
            self.latest_timestamp = timestamp
        elif timestamp > self.latest_timestamp:
            self.latest_timestamp = timestamp

    def summary_data(self) -> List[str]:
        timestamp = NOT_AVAILABLE
        if self.latest_timestamp != NOT_AVAILABLE:
            timestamp = str(
                zulu.Zulu.fromtimestamp(self.latest_timestamp).format(
                    "YYYY-MM-ddTHH:mm:ss"
                )
            )
        exe = "MULTIPLE" if self.multiple_exes else self.ref_proc["exe"]
        rv = [
            self.ref_proc["name"],
            exe,
            "YES" if self.root else "NO",
            str(self.count),
            timestamp,
        ]
        return rv


def processes_stream_output_summary(
    ctx: cfg.Context,
    muids: List[str],
    time: Tuple[float, float],
    pipeline=None,
    limit_mem=False,
) -> str:
    groups: Dict[Tuple, ProcessGroup] = {}
    for proc in api.get_processes(
        *ctx.get_api_data(), muids, time, pipeline, limit_mem
    ):
        multiple_exes, key = _key(proc)
        if key not in groups:
            groups[key] = ProcessGroup(multiple_exes)
        groups[key].add_proc(proc)
    data = []
    for group in groups.values():
        data.append(group.summary_data())
    rv = tabulate(
        sorted(
            data,
            key=lambda x: [x[0], x[2], lib.to_timestamp(x[4])],
        ),
        headers=SUMMARY_HEADERS,
        tablefmt="plain",
    )
    return rv


def _key(process: Dict) -> Tuple:
    name = process["name"]
    exe = process["exe"]
    if exe.endswith(name):
        return False, (name, exe)
    return True, name
