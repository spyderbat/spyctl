from typing import Dict, List, Optional, Tuple
import zulu
from tabulate import tabulate
import spyctl.spyctl_lib as lib


def spydertraces_output(spytrace: List[Dict]) -> Dict:
    if len(spytrace) == 1:
        return spytrace[0]
    elif len(spytrace) > 1:
        return {
            lib.API_FIELD: lib.API_VERSION,
            lib.ITEMS_FIELD: spytrace,
        }
    else:
        return {}


def time(epoch):
    return zulu.Zulu.fromtimestamp(epoch).format("YYYY-MM-ddTHH:mm:ss") + "Z"


def spydertraces_summary_output(spydertraces: List[Dict]) -> List:
    table_data = [
        [
            d["id"],
            d["trigger_short_name"],
            d["root_proc_name"],
            d["unique_flag_count"],
            d["object_count"],
            d["score"],
            time(d["valid_from"]),
        ]
        for d in spydertraces
    ]
    print(
        tabulate(
            table_data,
            headers=[
                "TRIGGER_NAME",
                "ROOT_PROCESS",
                "UNIQUE_FLAGS",
                "OBJECTS",
                "SCORE",
                "START_TIME",
            ],
            tablefmt="simple",
        )
    )


def spydertraces_output_wide(spydertrace: List) -> str:
    table_data = [
        [
            a["id"],
            a["trigger_short_name"],
            a["root_proc_name"],
            a["unique_flag_count"],
            a["object_count"],
            a["score"],
            a["process_count"],
            a["depth"],
            a["machines"],
            a["connection_count"],
            time(a["valid_from"]),
        ]
        for a in spydertrace
    ]
    print(
        tabulate(
            table_data,
            headers=[
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
            ],
            tablefmt="simple",
        )
    )
