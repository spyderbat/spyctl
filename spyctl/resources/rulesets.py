from typing import Dict, List

from tabulate import tabulate

import spyctl.spyctl_lib as lib

SUMMARY_HEADERS = [
    "UID",
    "NAME",
    "TYPE",
    "VERSION",
    "CREATE_TIME",
    "LAST_UPDATED",
]


def rulesets_summary_output(rulesets: List[Dict]):
    data = []
    for rs in rulesets:
        data.append(
            [
                rs[lib.METADATA_FIELD][lib.METADATA_UID_FIELD],
                rs[lib.METADATA_FIELD][lib.METADATA_NAME_FIELD],
                rs[lib.METADATA_FIELD][lib.METADATA_TYPE_FIELD],
                rs[lib.METADATA_FIELD][lib.METADATA_VERSION_FIELD],
                rs[lib.METADATA_FIELD][lib.METADATA_CREATE_TIME],
                rs[lib.METADATA_FIELD][lib.METADATA_LAST_UPDATE_TIME],
            ]
        )
    return tabulate(data, headers=SUMMARY_HEADERS)
