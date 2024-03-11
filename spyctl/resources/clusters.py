"""Handles cluster-specific spyctl functions"""

from typing import Dict, List

from tabulate import tabulate

import spyctl.config.configs as cfg
from spyctl import api

CLUSTER_CACHE = []


def clusters_summary_output(clusters: List[Dict]) -> str:
    """
    Generate a summary output of clusters.

    Args:
        clusters (List[Dict]): A list of dictionaries representing clusters.

    Returns:
        str: A formatted summary output of clusters.

    """
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


def cluster_exists(cluster_name_or_uid: str) -> bool:
    """
    Check if a cluster with the given name or UID exists.

    Args:
        cluster_name_or_uid (str): The name or UID of the cluster to check.

    Returns:
        bool: True if the cluster exists, False otherwise.
    """
    if not CLUSTER_CACHE:
        ctx = cfg.get_current_context()
        CLUSTER_CACHE.extend(api.get_clusters(*ctx.get_api_data()))
    for cluster in CLUSTER_CACHE:
        if cluster_name_or_uid in [cluster["name"], cluster["uid"]]:
            return True
    return False
