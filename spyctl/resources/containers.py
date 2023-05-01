from typing import Dict, List

import spyctl.spyctl_lib as lib
from tabulate import tabulate
import zulu

NOT_AVAILABLE = lib.NOT_AVAILABLE


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


def calc_age(time_float):
    creation_timestamp = zulu.parse(time_float)
    age_delta = zulu.now() - creation_timestamp
    if age_delta.days > 0:
        age = f"{age_delta.days}d"
        return age
    elif age_delta.seconds >= 3600:
        age = f"{age_delta.seconds // 3600}h"
        return age
    elif age_delta.seconds < 3600:
        age = f"{age_delta.seconds//60}m"
        return age


def container_summary_output(containers: List[Dict]) -> str:
    data = []
    for c in containers:
        if c["status"] == "closed":
            age = "N/A"
        else:
            age = calc_age(c["valid_from"])
        data.append(
            [
                c["image"],
                c["status"],
                c["id"],
                age,
            ]
        )
    data.sort(key=lambda x: (x[0], x[1]))
    print(
        tabulate(
            data,
            headers=["IMAGE", "STATUS", "UID", "AGE"],
            tablefmt="simple",
        )
    )
