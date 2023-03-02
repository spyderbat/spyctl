from typing import Dict, List

from tabulate import tabulate

import spyctl.spyctl_lib as lib
import zulu

NOT_AVAILABLE = lib.NOT_AVAILABLE


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


def processes_output_summary(procs: List[Dict]) -> str:
    headers = [
        "NAME",
        "EXE",
        "ROOT_EXECUTION",
        "COUNT",
        "LATEST_EXECUTED",
    ]
    groups = {}
    for proc in procs:
        multiple_exes, key = _key(proc)
        if key not in groups:
            groups[key] = ProcessGroup(multiple_exes)
        groups[key].add_proc(proc)
    data = []
    for group in groups.values():
        data.append(group.summary_data())
    output = tabulate(
        sorted(
            data,
            key=lambda x: [x[0], x[2], _to_timestamp(x[4])],
        ),
        headers=headers,
        tablefmt="plain",
    )
    return output + "\n"


def _key(process: Dict):
    name = process["name"]
    exe = process["exe"]
    if exe.endswith(name):
        return False, (name, exe)
    return True, name


def _to_timestamp(zulu_str):
    return zulu.Zulu.parse(zulu_str).timestamp()


def processes_output(procs: List[Dict]) -> Dict:
    if len(procs) == 1:
        return procs[0]
    elif len(procs) > 1:
        return {
            lib.API_FIELD: lib.API_VERSION,
            lib.ITEMS_FIELD: procs,
        }
    else:
        return {}
