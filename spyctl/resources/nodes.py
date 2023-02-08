from typing import Dict, List

from tabulate import tabulate

import spyctl.spyctl_lib as lib
import zulu


def nodes_output_summary(nodes: List[Dict]) -> str:
    headers = [
        "NAME",
        "STATUS",
        "AGE",
        "UID",
        "CLUSTER",
        "MUID",
    ]
    data = []
    for node in nodes:
        data.append(node_output_summary(node))
    output = tabulate(
        sorted(data, key=lambda x: [x[4], x[1], x[2], x[0]]),
        headers=headers,
        tablefmt="plain",
    )
    return output + "\n"


def node_output_summary(node: Dict) -> List[str]:
    creation_timestamp = zulu.parse(
        node[lib.METADATA_FIELD]["creationTimestamp"]
    )
    cluster = node.get("cluster_name")
    if not cluster:
        cluster = node["cluster_uid"]
    rv = [
        node[lib.METADATA_FIELD][lib.METADATA_NAME_FIELD],
        node["status"],
        f"{(zulu.now() - creation_timestamp).days}d",
        node["id"],
        cluster,
        node.get("muid", lib.NOT_AVAILABLE),
    ]
    return rv


def nodes_output(nodes: List[Dict]) -> Dict:
    if len(nodes) == 1:
        return nodes[0]
    elif len(nodes) > 1:
        return {
            lib.API_FIELD: lib.API_VERSION,
            lib.ITEMS_FIELD: nodes,
        }
    else:
        return {}
