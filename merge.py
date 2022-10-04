import ipaddress as ipaddr
from typing import Dict, Generator, List, Optional, TypeVar, Union
from typing_extensions import Self
from os import path

import yaml


T1 = TypeVar('T1')
def find(obj_list: List[T1], obj: T1) -> Optional[T1]:
    for candidate in obj_list:
        if candidate == obj:
            return candidate
    return None


def make_wildcard(strs: List[str]):
    if len(strs) == 1:
        return strs[0]
    ret = ""
    for chars in zip(*strs):
        if chars[:-1] != chars[1:]:
            return ret + '*'
        ret += chars[0]
    comp = len(strs[0])
    for name in strs:
        if len(name) != comp:
            return ret + '*'
    return ret


class ProcessID():
    def __init__(self, ident: str) -> None:
        self.id = ident
        self.unique_id = ident
        self.index = current_fingerprint
        self.matching: List[Self] = []
    
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.id == other.id \
                and self.index == other.index
        else:
            return False
    
    def extend(self, other: Self):
        self.matching.append(other)
        try:
            while True:
                ProcessID.all_ids.remove(other)
        except ValueError:
            pass
    
    all_ids: List[Self] = []

    @staticmethod
    def unique_all_ids():
        used = set()
        for proc_id in ProcessID.all_ids:
            while proc_id.unique_id in used:
                try:
                    last_num = int(proc_id.unique_id[-1])
                    proc_id.unique_id = proc_id.unique_id[:-1] + str(last_num + 1)
                except ValueError:
                    proc_id.unique_id += f"_{proc_id.index}"
            used.add(proc_id.unique_id)

    @staticmethod
    def unified_id(ident: str) -> str:
        proc_id = ProcessID(ident)
        for other_id in ProcessID.all_ids:
            if proc_id in other_id.matching or proc_id == other_id:
                return other_id.unique_id
        raise ValueError(f"ID {ident} did not match any processes")

class ProcessNode():
    def __init__(self, node: Dict) -> None:
        self.node = node.copy()
        self.id = ProcessID(node['id'])
        self.children = []
        self.appearances = set((current_fingerprint,))
        if 'children' in self.node:
            self.children = [ProcessNode(child) for child in self.node['children']]
        ProcessID.all_ids.append(self.id)
    
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if self.node.get('name') != other.node.get('name'):
                return False
            if self.node.get('euser') != other.node.get('euser'):
                return False
            # exe field is a list - does that need handling?
            self_exe = path.split(self.node['exe'][0])
            other_exe = path.split(other.node['exe'][0])
            if self_exe[0] == other_exe[0] and self_exe[1] != other_exe[1]:
                self_start = self_exe[1][:3]
                other_start = other_exe[1][:3]
                merged = make_wildcard((self.node['exe'][0], other.node['exe'][0]))
                if self_start == other_start:
                    new_exe = input(f"Merge {self.node['exe'][0]} and {other.node['exe'][0]} to {merged}? (y/n/custom merge): ")
                    if new_exe.lower() == 'y':
                        new_exe = merged
                    if new_exe.lower() != 'n':
                        self.node['exe'][0] = new_exe
                        other.node['exe'][0] = new_exe
            return self.node.get('exe') == other.node.get('exe')
        else:
            return False
    
    def extend(self, other: Self):
        if other != self:
            raise ValueError("Other process did not match")
        self.id.extend(other.id)
        self.appearances.update(other.appearances)
        for child in other.children:
            match = find(self.children, child)
            if match is not None:
                match.extend(child)
            else:
                self.children.append(child)
    
    def update_node(self):
        self.node['id'] = self.id.unique_id
        if len(self.children) == 0:
            if 'children' in self.node:
                del self.node['children']
            return
        self.node['children'] = self.children
        for child in self.children:
            child.update_node()


class ConnectionBlock():
    def __init__(self, node: Dict = None, ip: ipaddr.IPv4Network = None) -> None:
        if ip is not None:
            node = {
                'ipBlock': {
                    'cidr': str(ip)
                }
            }
        elif node is not None:
            node = node.copy()
        else:
            raise ValueError("ConnectionBlock given no parameters")
        self.ip = 'ipBlock' in node
        self.dns = 'dnsSelector' in node
        if self.dns:
            node['dnsSelector'] = [dns.lower() for dns in node['dnsSelector']]
        self.node = node
        self.appearances = set((current_fingerprint,))
    
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.node == other.node
        else:
            return False
    
    def extend(self, other: Self):
        if other != self:
            raise ValueError("Other connection not did not match")
        self.appearances.update(other.appearances)
    
    def as_network(self) -> Optional[ipaddr.IPv4Network]:
        if not self.ip:
            return None
        try:
            cidr = self.node['ipBlock']['cidr']
            return ipaddr.IPv4Network(cidr)
        except ValueError:
            return None

class ConnectionNode():
    def __init__(self, node: Dict) -> None:
        self.node = node.copy()
        self.has_from = 'from' in self.node
        if self.has_from:
            self.node['from'] = [ConnectionBlock(node=conn) for conn in self.node['from']]
        self.has_to = 'to' in self.node
        if self.has_to:
            self.node['to'] = [ConnectionBlock(node=conn) for conn in self.node['to']]
        self.appearances = set((current_fingerprint,))
        self.collapse_ips()
        self.unify_ids()
    
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.has_from == other.has_from \
                and self.has_to == other.has_to \
                and self.procs == other.procs \
                and self.ports == other.ports
        else:
            return False
    
    @property
    def procs(self):
        return self.node['processes']
    
    @property
    def ports(self):
        return self.node['ports']
    
    def extend_key(self, other_node, key):
        conn: ConnectionBlock
        for conn in other_node[key]:
            match = find(self.node[key], conn)
            if match is not None:
                match.extend(conn)
            else:
                self.node[key].append(conn)

    def extend(self, other: Self):
        if other != self:
            raise ValueError("Other connection node not did not match")
        if self.has_from:
            self.extend_key(other.node, 'from')
        if self.has_to:
            self.extend_key(other.node, 'to')
        self.appearances.update(other.appearances)
        # self.collapse_ips()
    
    def collapsed_cidrs(self, key):
        # would need to keep track of appearances somehow
        to_collapse = []
        ret = []
        block: ConnectionBlock
        for block in self.node[key]:
            network = block.as_network()
            if network is None:
                ret.append(block)
            else:
                to_collapse.append(network)
        ret += [ConnectionBlock(ip=add) for add in ipaddr.collapse_addresses(to_collapse)]
        return ret
    
    def collapse_ips(self):
        if self.has_from:
            self.node['from'] = self.collapsed_cidrs('from')
        if self.has_to:
            self.node['to'] = self.collapsed_cidrs('to')
    
    def unify_ids(self):
        new_proc = []
        for proc in self.procs:
            new_proc.append(ProcessID.unified_id(proc))
        self.node['processes'] = new_proc


class DiffDumper(yaml.Dumper):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_representer(ProcessNode, self.class_representer)
        self.add_representer(ConnectionNode, self.class_representer)
        self.add_representer(ConnectionBlock, self.class_representer)
    
    @staticmethod
    def class_representer(dumper: yaml.Dumper, data: Union[ProcessNode, ConnectionNode]):
        tag = f"!Appearances:{','.join([str(i) for i in data.appearances])}"
        return dumper.represent_mapping(tag, data.node)

class MergeDumper(yaml.Dumper):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_representer(ProcessNode, self.class_representer)
        self.add_representer(ConnectionNode, self.class_representer)
        self.add_representer(ConnectionBlock, self.class_representer)
    
    @staticmethod
    def class_representer(dumper: yaml.Dumper, data: Union[ProcessNode, ConnectionNode]):
        return dumper.represent_dict(data.node)


current_fingerprint = 0

T2 = TypeVar('T2')
def iter_prints(objs: List[T2]) -> Generator[T2, None, None]:
    global current_fingerprint
    for i, obj in enumerate(objs):
        current_fingerprint = i
        yield obj


def merge_subs(objs, key, ret):
    sub_list = None
    try:
        sub_list = [obj[key].copy() for obj in objs]
    except AttributeError:
        sub_list = [obj[key] for obj in objs]
    except KeyError:
        return
    ret[key] = globals()[f"merge_{key}"](sub_list)


def merge_fingerprints(fingerprints):
    if len(fingerprints) == 0:
        raise ValueError("Cannot merge 0 fingerprints")
    new_obj = dict()
    merge_subs(fingerprints, "spec", new_obj)
    merge_subs(fingerprints, "metadata", new_obj)
    return new_obj


def merge_metadata(metadatas):
    new_obj = dict()
    merge_subs(metadatas, "name", new_obj)
    return new_obj


def merge_name(names):
    return names[0]


def merge_spec(fingerprints):
    new_obj = dict()
    merge_subs(fingerprints, "serviceSelector", new_obj)
    merge_subs(fingerprints, "machineSelector", new_obj)
    merge_subs(fingerprints, "processPolicy", new_obj)
    merge_subs(fingerprints, "networkPolicy", new_obj)
    # metadata probably removed
    return new_obj


def merge_serviceSelector(selectors):
    if selectors[:-1] != selectors[1:]:
        # todo: handle better
        raise ValueError("Services to be merged did not match")
    return selectors[0]


def merge_machineSelector(selectors):
    new_obj = dict()
    merge_subs(selectors, 'hostname', new_obj)
    return new_obj


def merge_hostname(hostnames: List[str]):
    return make_wildcard(hostnames)


def merge_processPolicy(profiles):
    ret: List[ProcessNode] = []
    ProcessID.all_ids = []
    for proc_list in iter_prints(profiles):
        for proc in proc_list:
            obj = ProcessNode(proc)
            match = find(ret, obj)
            if match is not None:
                match.extend(obj)
            else:
                ret.append(obj)
    ProcessID.unique_all_ids()
    for proc in ret:
        proc.update_node()
    return ret


def merge_networkPolicy(profiles):
    new_obj = dict()
    merge_subs(profiles, "ingress", new_obj)
    merge_subs(profiles, "egress", new_obj)
    return new_obj


def merge_ingress(conns: List[List[Dict]]):
    ret: List[ConnectionNode] = []
    # uses ConnectionNode.__eq__ to find matches
    # and ConnectionNode.extend to merge matching nodes
    for conn_list in iter_prints(conns):
        for conn in conn_list:
            obj = ConnectionNode(conn)
            match = find(ret, obj)
            if match is not None:
                match.extend(obj)
            else:
                ret.append(obj)
    return ret


def merge_egress(conns: List[List[Dict]]):
    ret: List[ConnectionNode] = []
    # uses ConnectionNode.__eq__ to find matches
    # and ConnectionNode.extend to merge matching nodes
    for conn_list in iter_prints(conns):
        for conn in conn_list:
            obj = ConnectionNode(conn)
            if obj in ret:
                ret[ret.index(obj)].extend(obj)
            else:
                ret.append(obj)
    return ret
