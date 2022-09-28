import ipaddress as ipaddr
from typing import Dict, List, Optional
from typing_extensions import Self


def find(obj_list, obj):
    for candidate in obj_list:
        if candidate == obj:
            return candidate
    return None


class ProcessNode():
    def __init__(self, node: Dict) -> None:
        self.node = node
        self.node['id'] = f"{node['id']}_{current_fingerprint}"
        self.matching_ids = []
        self.children = []
        if 'children' in node:
            self.children = [ProcessNode(child) for child in node['children']]
    
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            compare_keys = ['name', 'exe', 'euser']
            for key in compare_keys:
                if self.node.get(key) != other.node.get(key):
                    return False
            # return self.children == other.children
            return True
        else:
            return False
    
    @property
    def id(self):
        return self.node['id']
    
    def extend(self, other: Self):
        if other != self:
            raise ValueError("Other process did not match")
        self.matching_ids.append(other.id)
        for child in other.children:
            match = find(ProcessNode.all_nodes, child)
            if match is not None:
                match.extend(child)
            else:
                ProcessNode.add(child)
                self.children.append(child)
        self.update_children()
    
    def update_children(self):
        if len(self.children) == 0:
            if 'children' in self.node:
                del self.node['children']
            return
        self.node['children'] = []
        for child in self.children:
            child.update_children()
            self.node['children'].append(child.node)
    
    all_nodes: List[Self] = []

    @staticmethod
    def add(obj: Self):
        ProcessNode.all_nodes.append(obj)
        for child in obj.children:
            match = find(ProcessNode.all_nodes, child)
            if match is not None:
                match.extend(child)
            else:
                ProcessNode.add(child)

    @staticmethod
    def unified_id(ident: str) -> str:
        ident = f"{ident}_{current_fingerprint}"
        for node in ProcessNode.all_nodes:
            if ident in node.matching_ids or ident == node.id:
                return node.id
        import pdb; pdb.set_trace()
        raise ValueError(f"ID {ident} did not match any processes")


class ConnectionNode():
    def __init__(self, node: Dict) -> None:
        self.has_from = 'from' in node
        self.has_to = 'to' in node
        self.node = node
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
    
    def extend(self, other: Self):
        if other != self:
            raise ValueError("Other connection not did not match")
        if self.has_from:
            self.node['from'] += other.node['from']
        if self.has_to:
            self.node['to'] += other.node['to']
        self.collapse_ips()
        
    def collapsed_cidrs(self, key):
        to_collapse = []
        ret = []
        for block in self.node[key]:
            if not 'ipBlock' in block:
                ret.append(block)
                continue
            cidr = block['ipBlock']['cidr']
            try:
                to_collapse.append(ipaddr.IPv4Network(cidr))
            except ValueError:
                ret.append(block)
                continue
        ret += [{ 'ipBlock': { 'cidr': str(add) } }
            for add in ipaddr.collapse_addresses(to_collapse)
        ]
        return ret
    
    def collapse_ips(self):
        if self.has_from:
            self.node['from'] = self.collapsed_cidrs('from')
        if self.has_to:
            self.node['to'] = self.collapsed_cidrs('to')
    
    def unify_ids(self):
        new_proc = []
        for proc in self.procs:
            new_proc.append(ProcessNode.unified_id(proc))
        self.node['processes'] = new_proc


current_fingerprint = 0

def iter_prints(objs):
    global current_fingerprint
    for i, obj in enumerate(objs):
        current_fingerprint = i
        yield obj


def merge_subs(objs, key, ret):
    sub_list = [obj[key] for obj in objs]
    ret[key] = globals()[f"merge_{key}"](sub_list)


def merge_fingerprints(fingerprints):
    new_obj = dict()
    merge_subs(fingerprints, "spec", new_obj)
    # metadata
    return new_obj


def merge_spec(fingerprints):
    new_obj = dict()
    merge_subs(fingerprints, "proc_profile", new_obj)
    merge_subs(fingerprints, "conn_profile", new_obj)
    # machineSelector, serviceSelector
    return new_obj


def merge_proc_profile(profiles):
    ret: List[ProcessNode] = []
    ProcessNode.all_nodes = []
    for proc_list in iter_prints(profiles):
        for proc in proc_list:
            obj = ProcessNode(proc)
            match = find(ProcessNode.all_nodes, obj)
            if match is not None:
                match.extend(obj)
            else:
                ProcessNode.add(obj)
                ret.append(obj)
    return [node.node for node in ret]


def merge_conn_profile(profiles):
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
    return [node.node for node in ret]


def merge_egress(conns):
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
    return [node.node for node in ret]
