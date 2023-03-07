from typing import Dict, List

from tabulate import tabulate

import spyctl.spyctl_lib as lib


def deployment_summary_output(deployment: Dict) -> List[str]:
    meta = deployment[lib.METADATA_FIELD]
    rv = [
        meta["name"],
        meta[lib.NAMESPACE_FIELD],
        deployment["cluster_name"] or deployment["cluster_uid"],
        deployment[lib.SPEC_FIELD]["replicas"],
    ]
    return rv


def deployments_summary_output(deployments: List[Dict]) -> str:
    headers = ["NAME", "NAMESPACE", "CLUSTER", "REPLICAS"]
    data = [deployment_summary_output(d) for d in deployments]
    output = tabulate(
        sorted(data, key=lambda x: [x[2], x[1], x[0]]),
        headers=headers,
        tablefmt="plain",
    )
    return output + "\n"


def deployments_output(deployments: List[Dict]) -> Dict:
    if len(deployments) == 1:
        return deployments[0]
    elif len(deployments) > 1:
        return {
            lib.API_FIELD: lib.API_VERSION,
            lib.ITEMS_FIELD: deployments,
        }
    else:
        return {}
