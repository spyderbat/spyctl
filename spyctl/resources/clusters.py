from typing import Dict, List

from tabulate import tabulate
import spyctl.spyctl_lib as lib


def clusters_summary_output(clusters: List[Dict]) -> str:
    header = ["NAME", "UID", "CLUSTER_ID", "FIRST_SEEN", "LAST_DATA"]
    data = []
    for cluster in clusters:
        data.append(cluster_summary_data(cluster))
    return tabulate(data, header, tablefmt="plain")


def cluster_summary_data(cluster: Dict) -> List:
    rv = [
        cluster["name"],
        cluster["uid"],
        cluster["cluster_details"]["cluster_id"],
        cluster["cluster_details"]["first_seen"],
        cluster["cluster_details"]["last_data"],
    ]
    return rv


def clusters_output(clusters: List[Dict]) -> Dict:
    if len(clusters) == 1:
        return clusters[0]
    elif len(clusters) > 1:
        return {
            lib.API_FIELD: lib.API_VERSION,
            lib.ITEMS_FIELD: clusters,
        }
    else:
        return {}
