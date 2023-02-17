from typing import Dict, List

from tabulate import tabulate

import spyctl.spyctl_lib as lib
import zulu
import ipaddress

NOT_AVAILABLE = lib.NOT_AVAILABLE


class ConnectionGroup:
    def __init__(self) -> None:
        self.ref_conn = None
        self.latest_timestamp = NOT_AVAILABLE
        self.count = 0
        self.ip = None

    def add_conn(self, conn: Dict):
        self.__update_latest_timestamp(conn.get("create_time"))
        if self.ref_conn is None:
            self.ref_conn = conn
        self.count += 1
        ip = ipaddress.ip_address(conn["remote_ip"])
        if self.ip is None:
            self.ip = ip.exploded
        else:
            self.ip = _loose_abbrev_ips(self.ip, ip.exploded)

    def __update_latest_timestamp(self, timestamp):
        if timestamp is None:
            return
        if self.latest_timestamp == NOT_AVAILABLE:
            self.latest_timestamp = timestamp
        elif timestamp > self.latest_timestamp:
            self.latest_timestamp = timestamp

    def summary_data(self, ignore_ips) -> List[str]:
        timestamp = NOT_AVAILABLE
        if self.latest_timestamp != NOT_AVAILABLE:
            timestamp = str(
                zulu.Zulu.fromtimestamp(self.latest_timestamp).format(
                    "YYYY-MM-ddTHH:mm:ss"
                )
            )
        rv = [
            # self.ref_conn["remote_ip"],
            # self.ref_conn["remote_port"],
            _shorten_v6(self.ip),
            self.ref_conn["direction"],
            self.ref_conn["proc_name"],
            str(self.count),
            timestamp,
        ]
        if ignore_ips:
            rv = rv[1:]
        return rv


def connections_output_summary(conns: List[Dict], ignore_ips=False) -> str:
    headers = [
        "DESTINATION_IP",
        # "DESTINATION_PORT",
        "DIRECTION",
        "PROCESS_NAME",
        "COUNT",
        "LATEST_TIMESTAMP",
    ]
    if ignore_ips:
        headers = headers[1:]
    groups = {}
    for conn in conns:
        key = _key(conn, ignore_ips)
        if key not in groups:
            groups[key] = ConnectionGroup()
        groups[key].add_conn(conn)
    data = []
    for group in groups.values():
        data.append(group.summary_data(ignore_ips))
    sort_key = (
        (lambda x: [x[0], x[1]])
        if ignore_ips
        else (lambda x: [x[1], x[0], x[2]])
    )
    output = tabulate(
        sorted(data, key=sort_key),
        headers=headers,
        tablefmt="plain",
    )
    return output + "\n"


def _key(connection: Dict, ignore_ips):
    if ignore_ips:
        return (
            connection["direction"],
            connection["proc_name"],
        )
    ip = ipaddress.ip_address(connection["remote_ip"])
    # just like the unnecessary complexity of this summary
    ip_str = ip.exploded
    found = 0
    for i, char in enumerate(ip_str):
        if not char.isdigit():
            found += 1
            if found == 2:
                ip_str = ip_str[: i + 1]
                break
    return (
        ip.version,
        ip_str,
        connection["direction"],
        connection["proc_name"],
    )


def _loose_abbrev_ips(ip1, ip2):
    if ip1 == ip2:
        return ip1
    ret = ""
    for char1, char2 in zip(ip1, ip2):
        if char1 == char2:
            ret += char1
        else:
            ret += "*"
            return ret
    return ret + "*"


def _shorten_v6(ip):
    if ":" not in ip:
        return ip
    ip = ip.replace("0000", "zero")
    i = 0
    pos = -1
    most = 0
    last = 0
    num = 0
    while i < len(ip):
        if ip[i : i + 4] == "zero":
            if num == 0:
                last = i
            num += 1
            if num > most:
                most = num
                pos = last
        else:
            num = 0
        i += 5
    len_diff = 39 - len(ip)
    if ip.endswith("*"):
        len_diff += 1
    if pos != -1:
        ip = ip[:pos] + ":" + ip[pos + most * 5 :]
        if pos == 0:
            ip = ":" + ip
    ip = ip.replace("0", "")
    ip = ip.replace("zero", "0")
    if len_diff > 0:
        ip += f" (+{len_diff})"
    return ip


def connections_output(conns: List[Dict]) -> Dict:
    if len(conns) == 1:
        return conns[0]
    elif len(conns) > 1:
        return {
            lib.API_FIELD: lib.API_VERSION,
            lib.ITEMS_FIELD: conns,
        }
    else:
        return {}
