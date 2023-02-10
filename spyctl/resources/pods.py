from typing import Dict, List

from tabulate import tabulate

import spyctl.spyctl_lib as lib
import zulu

pod_status = {}


def pods_output_summary(pods: List[Dict]) -> str:
    global pod_status
    pod_status = {}
    headers = [
        "NAME",
        "UID",
        "CLUSTER",
        "READY",
        "LAST_STATUS_SEEN",
        "AGE",
        "LAST_SEEN_BY_SPYDERBAT",
        "SPYDERBAT_STATUS",
    ]
    data = []
    for pod in pods:
        phase = pod["k8s_status"]["phase"]
        if phase == "Running":
            pod_status[pod["id"]] = "1/1"
        elif phase in {"Pending", "Failed"}:
            pod_status[pod["id"]] = "0/1"
        else:
            pod_status[pod["id"]] = "N/A"
    for pod in pods:
        data.append(pod_summary_data(pod))
    output = tabulate(
        sorted(data, key=lambda x: [x[2], x[7], x[0], _to_timestamp(x[6])]),
        headers=headers,
        tablefmt="plain",
    )
    return output + "\n"


def _to_timestamp(zulu_str):
    return zulu.Zulu.parse(zulu_str).timestamp()


def pod_summary_data(pod: Dict) -> List:
    creation_timestamp = zulu.parse(
        pod[lib.METADATA_FIELD]["creationTimestamp"]
    )
    cluster = pod.get("cluster_name") or pod.get("cluster_uid")
    if not cluster:
        cluster = "N/A"
    rv = [
        pod[lib.METADATA_FIELD][lib.METADATA_NAME_FIELD],
        pod["id"],
        cluster,
        pod_status[pod["id"]],
        pod["k8s_status"]["phase"],
        f"{(zulu.now() - creation_timestamp).days}d",
        str(zulu.Zulu.fromtimestamp(pod["time"]).format("YYYY-MM-ddTHH:mm:ss"))
        + "Z",
        pod["status"],
    ]
    return rv


def pods_output(pods: List[Dict]) -> Dict:
    if len(pods) == 1:
        return pods[0]
    elif len(pods) > 1:
        return {
            lib.API_FIELD: lib.API_VERSION,
            lib.ITEMS_FIELD: pods,
        }
    else:
        return {}


def pod_output(pod: Dict) -> Dict:
    rv = {
        lib.API_FIELD: "v1",
        lib.KIND_FIELD: pod[lib.KIND_FIELD],
        lib.METADATA_FIELD: pod[lib.METADATA_FIELD],
        lib.SPEC_FIELD: pod[lib.SPEC_FIELD],
        lib.STATUS_FIELD: pod["k8s_status"],
    }
    return rv
