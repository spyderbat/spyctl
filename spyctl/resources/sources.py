from typing import Dict, List

from tabulate import tabulate

import spyctl.spyctl_lib as lib


def sources_summary_output(sources: List[Dict]):
    headers = ["NAME", "UID", "REGISTRATION_DATE", "LAST_DATA"]
    data = []
    for source in sources:
        data.append(source_summary_data(source))
    data.sort(key=lambda x: [x[0], lib.to_timestamp(x[3])])
    return tabulate(data, headers, tablefmt="plain")


def source_summary_data(source: Dict):
    rv = [
        source["name"],
        source["uid"],
        source["valid_from"],
        source["last_data"],
    ]
    return rv


def sources_output(sources: List[Dict]):
    if len(sources) == 1:
        return sources[0]
    elif len(sources) > 1:
        return {
            lib.API_FIELD: lib.API_VERSION,
            lib.ITEMS_FIELD: sources,
        }
    else:
        return {}
