from typing import Dict, List, Tuple

from tabulate import tabulate

import spyctl.api as api
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib

SUMMARY_HEADERS = [
    "IMAGE",
    "IMAGE_ID",
    "LATEST_TIMESTAMP",
    "COUNT",
    "NAMESPACE",
    "CLUSTER",
]


class ContainerGroup:
    def __init__(self) -> None:
        self.latest_timestamp = lib.NOT_AVAILABLE
        self.count = 0
        self.image = None
        self.image_id = None
        self.namespace = None
        self.cluster = None

    def add_container(self, cont: Dict):
        self.__update_latest_timestamp(cont.get("time"))
        self.count += 1
        if not self.image:
            self.image = cont["image"]
            self.image_id = cont["image_id"]
            self.namespace = cont.get("pod_namespace")
            self.cluster = cont.get("clustername") or cont.get("cluster_uid")

    def summary_data(self) -> List[str]:
        rv = [
            self.image,
            self.image_id,
            lib.epoch_to_zulu(self.latest_timestamp),
            self.count,
            self.namespace or lib.NOT_AVAILABLE,
            self.cluster or lib.NOT_AVAILABLE,
        ]
        return rv

    def __update_latest_timestamp(self, timestamp):
        if timestamp is None:
            return
        if self.latest_timestamp == lib.NOT_AVAILABLE:
            self.latest_timestamp = timestamp
        elif timestamp > self.latest_timestamp:
            self.latest_timestamp = timestamp


def cont_summary_output(
    ctx: cfg.Context,
    muids: List[str],
    time: Tuple[float, float],
    pipeline=None,
    limit_mem=False,
):
    cont_groups: Dict[str, ContainerGroup] = {}
    for container in api.get_containers(
        *ctx.get_api_data(),
        muids,
        time,
        pipeline=pipeline,
        limit_mem=limit_mem,
    ):
        key = __key(container)
        if key not in cont_groups:
            cont_groups[key] = ContainerGroup()
        cont_groups[key].add_container(container)
    data = []
    for group in cont_groups.values():
        data.append(group.summary_data())
    data.sort(key=lambda x: (x[5], x[0], x[1], x[4]))
    rv = tabulate(
        data,
        headers=SUMMARY_HEADERS,
        tablefmt="plain",
    )
    return rv


def cont_summary_data(container: Dict) -> List[str]:
    return [
        container[lib.BE_CONTAINER_IMAGE],
        container[lib.BE_CONTAINER_IMAGE_ID],
        container[lib.STATUS_FIELD],
        lib.calc_age(container[lib.VALID_FROM_FIELD]),
    ]


def __key(cont: Dict):
    return (
        cont["image"],
        cont["image_id"],
        cont.get("pod_namespace"),
        cont.get("cluster_name") or cont.get("cluster_uid"),
    )
