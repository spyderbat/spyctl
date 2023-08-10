from typing import IO, Dict, List, Set, Any

import ipaddress as ipaddr
import socket
from collections import defaultdict
import json
import tqdm
import sys

import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.filter_resource as filt
import spyctl.spyctl_lib as lib


def handle_describe(resource: str, name_or_uid: str, file: IO = None):
    if resource == lib.POLICIES_RESOURCE:
        handle_describe_policy(name_or_uid, file)


def handle_describe_policy(name_or_uid, file: IO = None):
    if not name_or_uid and not file:
        cli.err_exit("No file or name_or_uid provided")
    if not file:
        policy = get_policy_by_name_or_uid(name_or_uid)
    else:
        policy = get_policy_from_file(name_or_uid, file)
    pol_name = policy[lib.METADATA_FIELD][lib.METADATA_NAME_FIELD]
    cli.try_log(f"Describing policy '{pol_name}'")
    output = {
        "kind": policy[lib.KIND_FIELD],
        **policy[lib.METADATA_FIELD],
        "scope": describe_scope(policy[lib.SPEC_FIELD]),
    }
    output.update(describe_processes(policy[lib.SPEC_FIELD]))
    output.update(describe_connections(policy[lib.SPEC_FIELD]))
    cli.try_log("\n")
    cli.show(output, lib.OUTPUT_YAML)


def get_policy_from_file(name_or_uid: str, file: IO) -> Dict:
    resource = lib.load_resource_file(file)
    kind = resource[lib.KIND_FIELD]
    if kind != lib.POL_KIND:
        cli.err_exit(f"File kind '{kind}' is not '{lib.POL_KIND}'")
    if name_or_uid:
        policies = filt.filter_obj(
            [resource],
            [
                [lib.METADATA_FIELD, lib.METADATA_NAME_FIELD],
                [lib.METADATA_FIELD, lib.METADATA_UID_FIELD],
            ],
            name_or_uid,
        )
        if len(policies) == 0:
            cli.err_exit(f"No policies matching name_or_uid '{name_or_uid}'")
        resource = policies[0]
    type = resource[lib.METADATA_FIELD][lib.METADATA_TYPE_FIELD]
    if type not in lib.GUARDIAN_POL_TYPES:
        cli.err_exit(
            f"Policy type '{type}' is not a Guardian Policy type "
            f"'{lib.GUARDIAN_POL_TYPES}'"
        )
    return resource


def get_policy_by_name_or_uid(name_or_uid) -> Dict:
    ctx = cfg.get_current_context()
    policies = api.get_policies(*ctx.get_api_data())
    policies = filt.filter_obj(
        policies,
        [
            [lib.METADATA_FIELD, lib.METADATA_NAME_FIELD],
            [lib.METADATA_FIELD, lib.METADATA_UID_FIELD],
        ],
        name_or_uid,
    )
    if len(policies) == 0:
        cli.err_exit(f"No policies matching name_or_uid '{name_or_uid}'")
    if len(policies) > 1:
        cli.err_exit("Name or uid of policy is ambiguous")
    return policies[0]


def describe_scope(spec: Dict[str, Any]):
    rv = {}
    for key, value in spec.items():
        if key.endswith("Selector"):
            rv[key] = value
    return rv


def describe_processes(spec: Dict):
    proc_pol = spec[lib.PROC_POLICY_FIELD]
    proc_details = defaultdict(dict)
    users = set()
    node_count = [0]
    for proc in proc_pol:
        __get_proc_details(proc_details, users, node_count, proc)
    rv = {
        "Process Details": {
            "Total process nodes": node_count[0],
            "Effective users": list(users),
            "Processes": __sort_dict(__unset_dict(proc_details)),
        }
    }
    return rv


def __get_proc_details(
    proc_details: Dict[str, Dict],
    users: Set,
    node_count: List[int],
    proc: Dict,
):
    node_count[0] += 1
    name = proc[lib.NAME_FIELD]
    exes = proc[lib.EXE_FIELD]
    eusers = proc.get(lib.EUSER_FIELD, [])
    if name in proc_details:
        proc_details[name]["count"] += 1
        proc_details[name]["exes"].update(exes)
    else:
        proc_details[name]["count"] = 1
        proc_details[name]["exes"] = set(exes)
    users.update(eusers)
    children = proc.get(lib.CHILDREN_FIELD)
    if children:
        for child in children:
            __get_proc_details(proc_details, users, node_count, child)


def describe_connections(spec: Dict):
    net_pol = spec[lib.NET_POLICY_FIELD]
    ingress = net_pol[lib.INGRESS_FIELD]
    egress = net_pol[lib.EGRESS_FIELD]
    ips, hostnames, ports = extract_src_dst_info(ingress)
    i, h, p = extract_src_dst_info(egress)
    ips.update(i)
    hostnames.update(h)
    ports.update(p)
    dns_map, unknown_ips = __lookup_ips(ips)
    name_map, unknown_hostnames = __lookup_hostname(hostnames)
    for hostname, ip_set in name_map.items():
        if hostname in dns_map:
            dns_map[hostname].update(ip_set)
        else:
            dns_map[hostname] = ip_set
    rv = {
        "Connection Details": {
            "Total connection nodes": len(ingress) + len(egress),
            "Ports used": list(ports),
            "DNS MAP": {},
        }
    }
    rv["Connection Details"]["DNS MAP"].update(
        **__sort_dict(
            {h_name: list(ip_set) for h_name, ip_set in dns_map.items()}
        )
    )
    rv["Connection Details"]["DNS MAP"].update(
        **{"unknown ips": list(unknown_ips)}
    )
    rv["Connection Details"]["DNS MAP"].update(
        **{"unknown hostnames": list(unknown_hostnames)}
    )
    return rv


def extract_src_dst_info(ingress_or_egress):
    ips = set()
    hostnames = set()
    ports = set()
    for node in ingress_or_egress:
        block_list = node.get("from", node.get("to", {}))
        for block in block_list:
            if lib.IP_BLOCK_FIELD in block:
                ip = __eval_ip(block[lib.IP_BLOCK_FIELD][lib.CIDR_FIELD])
                if not ip:
                    continue
                ips.add(ip)
            elif lib.DNS_SELECTOR_FIELD in block:
                for name in block[lib.DNS_SELECTOR_FIELD]:
                    hostname = __eval_hostname(name)
                    if not hostname:
                        continue
                    hostnames.add(hostname)
        ports.update([p[lib.PORT_FIELD] for p in node[lib.PORTS_FIELD]])
    return ips, hostnames, ports


INCLUDE_PRIVATE = True


def __eval_ip(cidr: str):
    str_ip, bits = cidr.split("/")
    try:
        ip = ipaddr.IPv4Address(str_ip)
        if bits != "32":
            return None
        if ip.is_private and not INCLUDE_PRIVATE:
            return None
        return str_ip
    except ipaddr.AddressValueError:
        ip = ipaddr.IPv6Address(str_ip)
        if bits != "128":
            return None
        return str_ip


INCLUDE_LOCAL = True


def __eval_hostname(name: str):
    if not INCLUDE_LOCAL and name.endswith(".local"):
        return None
    return name


def __lookup_ips(ips: List[str]):
    if not ips:
        return {}, set()
    rv_map = defaultdict(set)
    unknown = set()
    cli.try_log("Looking up hostnames by IP")
    pbar = tqdm.tqdm(total=len(ips), leave=False, file=sys.stderr)
    for ip in ips:
        pbar.update(1)
        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
        except Exception:
            unknown.add(ip)
            continue
        rv_map[hostname].add(ip)
    return rv_map, unknown


def __lookup_hostname(hostnames: List[str]):
    if not hostnames:
        return {}, set()
    rv_map = defaultdict(set)
    unknown = set()
    cli.try_log("Looking up IPs by hostname")
    pbar = tqdm.tqdm(total=len(hostnames), leave=False, file=sys.stderr)
    for hostname in hostnames:
        pbar.update(1)
        try:
            ip = socket.gethostbyname(hostname)
        except Exception:
            unknown.add(hostname)
            continue
        rv_map[hostname].add(ip)
    return rv_map, unknown


def __unset_dict(_dict: Dict) -> Dict:
    for key, value in _dict.items():
        if isinstance(value, set):
            _dict[key] = list(value)
        elif isinstance(value, dict):
            for v_key, v in value.items():
                if isinstance(v, set):
                    value[v_key] = list(v)
                elif isinstance(v, dict):
                    value[v_key] = __unset_dict(v)
    return _dict


def __sort_dict(_dict) -> Dict:
    dict_str = json.dumps(_dict, sort_keys=True)
    return json.loads(dict_str)
