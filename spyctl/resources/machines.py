from typing import Dict, List

from tabulate import tabulate

import spyctl.spyctl_lib as lib


def machines_summary_output(machines: List[Dict]):
    headers = ["NAME", "UID", "REGISTRATION_DATE", "LAST_DATA"]
    data = []
    for machine in machines:
        data.append(machine_summary_data(machine))
    data.sort(key=lambda x: [x[0], lib._to_timestamp(x[3])])
    return tabulate(data, headers, tablefmt="plain")


def machine_summary_data(machine: Dict):
    rv = [
        machine["name"],
        machine["uid"],
        machine["valid_from"],
        machine["last_data"],
    ]
    return rv


def machines_output(machines: List[Dict]):
    if len(machines) == 1:
        return machines[0]
    elif len(machines) > 1:
        return {
            lib.API_FIELD: lib.API_VERSION,
            lib.ITEMS_FIELD: machines,
        }
    else:
        return {}
