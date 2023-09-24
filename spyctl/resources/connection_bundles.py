from typing import Dict, List, Tuple

from tabulate import tabulate

import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
import spyctl.api as api

SUMMARY_HEADERS = [
    "SERVER",
    "CLIENT",
    "SERVER_PORT",
    "CONNECTIONS",
    "LATEST_TIMESTAMP",
]


class ConnBunGroup:
    def __init__(self) -> None:
        self.ref_conn = None
        self.latest_timestamp = None
        self.count = 0
        self.conn_count = 0
        self.client_ip = None
        self.server_ip = None
        self.client_dns = None
        self.server_dns = None
        self.server_port = None

    def add_conn_bun(self, conn_bun: Dict):
        if not self.client_ip:
            self.client_ip = conn_bun[lib.CLIENT_IP]
        if not self.client_dns:
            self.client_dns = conn_bun.get(lib.CLIENT_DNS)
        if not self.server_ip:
            self.server_ip = conn_bun[lib.SERVER_IP]
        if not self.server_dns:
            self.server_dns = conn_bun.get(lib.SERVER_DNS)
        if self.server_port is None:
            self.server_port = conn_bun[lib.SERVER_PORT]
        self.count += 1
        self.conn_count += conn_bun[lib.NUM_CONNECTIONS]
        if (
            not self.latest_timestamp
            or self.latest_timestamp < conn_bun["time"]
        ):
            self.latest_timestamp = conn_bun["time"]

    def summary_data(self) -> List[str]:
        rv = [
            self.__dns_summary(self.server_dns) or self.server_ip,
            self.__dns_summary(self.client_dns) or self.client_ip,
            self.server_port,
            self.conn_count,
            lib.epoch_to_zulu(self.latest_timestamp),
        ]
        return rv

    def __dns_summary(self, dns_name: str) -> str:
        if not dns_name:
            return None
        names = dns_name.split(",")
        return names[0]


def conn_bun_summary_output(
    ctx: cfg.Context,
    muids: List[str],
    time: Tuple[float, float],
    pipeline=None,
    limit_mem=False,
):
    groups: Dict[tuple, ConnBunGroup] = {}
    for conn_bun in api.get_connection_bundles(
        *ctx.get_api_data(), muids, time, pipeline, limit_mem
    ):
        key = __make_key(conn_bun)
        if key not in groups:
            groups[key] = ConnBunGroup()
        groups[key].add_conn_bun(conn_bun)
    data = []
    for group in groups.values():
        data.append(group.summary_data())
    data.sort(key=lambda x: (x[0], x[2]))
    output = tabulate(
        data,
        headers=SUMMARY_HEADERS,
        tablefmt="plain",
    )
    return output


def __make_key(conn_bun: Dict):
    server = conn_bun.get(lib.SERVER_DNS) or conn_bun[lib.SERVER_IP]
    client = conn_bun.get(lib.CLIENT_DNS) or conn_bun[lib.CLIENT_IP]
    port = conn_bun[lib.SERVER_PORT]
    return (server, client, port)
