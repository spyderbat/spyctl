from typing import Dict, List

from tabulate import tabulate


def clusters_summary_output(clusters: List[Dict]) -> str:
    header = ["NAME", "UID", "CLUSTER_ID", "FIRST_SEEN", "LAST_DATA"]
    data = []
    for cluster in clusters:
        data.append(__cluster_summary_data(cluster))
    return tabulate(data, header, tablefmt="plain")


def __cluster_summary_data(cluster: Dict) -> List:
    rv = [
        cluster["name"],
        cluster["uid"],
        cluster["cluster_details"]["cluster_uid"],
        cluster["valid_from"],
        cluster["last_data"],
    ]
    return rv
