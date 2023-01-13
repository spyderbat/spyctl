from typing import Dict, List

from tabulate import tabulate

import spyctl.spyctl_lib as lib


def namespace_summary_output(namespaces: List[Dict]) -> str:
    output = ""
    header = ["NAMESPACE"]
    if len(namespaces) == 1:
        data = [
            [namespace] for namespace in next(iter(namespaces))["namespaces"]
        ]
        output = tabulate(data, headers=header, tablefmt="plain")
    elif len(namespaces) > 1:
        output = []
        for cluster_group in namespaces:
            cluster_key = (
                f"{cluster_group['cluster_name']}"
                f" - {cluster_group['cluster_uid']}"
            )
            output.append(cluster_key)
            data = [[namespace] for namespace in cluster_group["namespaces"]]
            if len(data) > 0:
                output.append(tabulate(data, header, tablefmt="plain") + "\n")
            else:
                output.append("No Namespace Data\n")
        output = "\n".join(output)
    return output


def namespaces_output(namespaces: List[Dict]) -> Dict:
    if len(namespaces) == 1:
        return namespaces[0]
    elif len(namespaces) > 1:
        return {
            lib.API_FIELD: lib.API_VERSION,
            lib.ITEMS_FIELD: namespaces,
        }
    else:
        return {}
