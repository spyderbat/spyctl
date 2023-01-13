import ipaddress as ipaddr
from os import path
from typing import Dict, Generator, List, Optional, TypeVar, Union
from difflib import SequenceMatcher

import yaml
from typing_extensions import Self

import spyctl.spyctl_lib as lib
import spyctl.cli as cli
import spyctl.resources.baselines as spyctl_baselines

T1 = TypeVar("T1")


def handle_merge(filename, with_file, latest, output):
    if not with_file and not latest:
        cli.err_exit("Nothing to merge")
    elif with_file and latest:
        cli.try_log("Latest and with-file detected. Only merging with file.")
        latest = False
    resource = lib.load_resource_file(filename)
    resrc_kind = resource.get(lib.KIND_FIELD)
    if with_file:
        with_resource = lib.load_resource_file(with_file)
    else:
        with_resource = None
    if resrc_kind == lib.BASELINE_KIND:
        spyctl_baselines.merge_baseline(
            resource, with_resource, latest, output
        )


def find(obj_list: List[T1], obj: T1) -> Optional[T1]:
    for candidate in obj_list:
        if candidate == obj:
            return candidate
    return None


def make_wildcard(strs: List[str]):
    if len(strs) == 1:
        return strs[0]
    ret = ""
    comp = len(strs[0])
    for name in strs:
        if len(name) != comp:
            ret = ret + "*"
    if ret == "*":
        # Simple substring match didn't work so lets see if there is a
        # better match (takes more computation)
        sub_str = strs[0]
        for name in strs[1:]:
            name = name.strip("*")
            match = SequenceMatcher(None, sub_str, name).find_longest_match(
                0, len(sub_str), 0, len(name)
            )
            sub_str = sub_str[match.a : match.a + match.size]
            if len(sub_str) < 3:
                break
        if len(sub_str) < 3:
            ret = "*"
        else:
            ret = "*" + sub_str + "*"
    return ret


class IfAllEqList:
    def __init__(self):
        self.objs = []
        self.prints = []

    def add_obj(self, obj):
        if obj not in self.objs:
            self.objs.append(obj)
            self.prints.append(f"!Appearances:{current_fingerprint}")
        else:
            idx = self.objs.index(obj)
            self.prints[idx] += f",{current_fingerprint}"

    def get_for_merge(self):
        if self.objs[1:] == self.objs[:-1]:
            return self.objs[0]
        return None

    def get_for_diff(self):
        return self.objs, self.prints


class WildcardList:
    def __init__(self):
        self.strs = []
        self.prints = []

    def add_str(self, string: str):
        if string not in self.strs:
            self.strs.append(string)
            self.prints.append(f"!Appearances:{current_fingerprint}")
        else:
            idx = self.strs.index(string)
            self.prints[idx] += f",{current_fingerprint}"

    def get_for_merge(self):
        return make_wildcard(self.strs)

    def get_for_diff(self):
        return self.strs, self.prints


class ProcessID:
    def __init__(self, ident: str) -> None:
        self.id = ident
        self.unique_id = ident
        self.index = current_fingerprint
        self.matching: List[Self] = []

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.id == other.id and self.index == other.index
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
                    proc_id.unique_id = proc_id.unique_id[:-1] + str(
                        last_num + 1
                    )
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


class ProcessNode:
    def __init__(self, node: Dict) -> None:
        self.node = node.copy()
        self.id = ProcessID(node["id"])
        self.children = []
        self.appearances = set((current_fingerprint,))
        if "children" in self.node:
            self.children = [
                ProcessNode(child) for child in self.node["children"]
            ]
        ProcessID.all_ids.append(self.id)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if self.node.get("name") != other.node.get("name"):
                return False
            if self.node.get("euser") != other.node.get("euser"):
                return False
            # exe field is a list - does that need handling?
            self_exe = path.split(self.node["exe"][0])
            other_exe = path.split(other.node["exe"][0])
            if self_exe[0] == other_exe[0] and self_exe[1] != other_exe[1]:
                self_start = self_exe[1][:3]
                other_start = other_exe[1][:3]
                merged = make_wildcard(
                    (self.node["exe"][0], other.node["exe"][0])
                )
                if self_start == other_start:
                    new_exe = input(
                        f"Merge {self.node['exe'][0]} and"
                        f" {other.node['exe'][0]} to {merged}?"
                        " (y/n/custom merge): "
                    )
                    if new_exe.lower() == "y":
                        new_exe = merged
                    if new_exe.lower() != "n":
                        self.node["exe"][0] = new_exe
                        other.node["exe"][0] = new_exe
            return self.node.get("exe") == other.node.get("exe")
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
        self.node["id"] = self.id.unique_id
        if len(self.children) == 0:
            if "children" in self.node:
                del self.node["children"]
            return
        self.node["children"] = self.children
        for child in self.children:
            child.update_node()


class ConnectionBlock:
    def __init__(
        self, node: Dict = None, ip: ipaddr.IPv4Network = None
    ) -> None:
        if ip is not None:
            node = {"ipBlock": {"cidr": str(ip)}}
        elif node is not None:
            node = node.copy()
        else:
            raise ValueError("ConnectionBlock given no parameters")
        self.ip = "ipBlock" in node
        self.dns = "dnsSelector" in node
        if self.dns:
            node["dnsSelector"] = [dns.lower() for dns in node["dnsSelector"]]
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
            cidr = self.node["ipBlock"]["cidr"]
            return ipaddr.IPv4Network(cidr)
        except ValueError:
            return None


class ConnectionNode:
    def __init__(self, node: Dict) -> None:
        self.node = node.copy()
        self.has_from = "from" in self.node
        if self.has_from:
            self.node["from"] = [
                ConnectionBlock(node=conn) for conn in self.node["from"]
            ]
        self.has_to = "to" in self.node
        if self.has_to:
            self.node["to"] = [
                ConnectionBlock(node=conn) for conn in self.node["to"]
            ]
        self.appearances = set((current_fingerprint,))
        self.unify_ids()

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (
                self.has_from == other.has_from
                and self.has_to == other.has_to
                and self.procs == other.procs
                and self.ports == other.ports
            )
        else:
            return False

    # def __contains__(self, item):
    #     if isinstance(item, self.__class__):
    #         return(
    #             self.has_from == item.has_from
    #             and self.has_to == item.has_to
    #             and self.ports == item.ports
    #             and self.
    #         )

    @property
    def procs(self):
        return self.node["processes"]

    @property
    def ports(self):
        return self.node["ports"]

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
            self.extend_key(other.node, "from")
        if self.has_to:
            self.extend_key(other.node, "to")
        self.appearances.update(other.appearances)
        # self.collapse_ips()

    def unify_ids(self):
        new_proc = []
        for proc in self.procs:
            new_proc.append(ProcessID.unified_id(proc))
        self.node["processes"] = new_proc


class DiffDumper(yaml.Dumper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_representer(ProcessNode, self.class_representer)
        self.add_representer(ConnectionNode, self.class_representer)
        self.add_representer(ConnectionBlock, self.class_representer)
        self.add_representer(IfAllEqList, self.list_representer)
        self.add_representer(WildcardList, self.list_representer)
        self.add_representer(DiffDumper.ListItem, self.list_item_representer)

    class ListItem:
        def __init__(self, tag, data):
            self.tag = tag
            self.data = data

    @staticmethod
    def class_representer(
        dumper: yaml.Dumper,
        data: Union[ProcessNode, ConnectionNode, ConnectionBlock],
    ):
        tag = f"!Appearances:{','.join([str(i) for i in data.appearances])}"
        return dumper.represent_mapping(tag, data.node)

    @staticmethod
    def list_representer(
        dumper: yaml.Dumper, data: Union[IfAllEqList, WildcardList]
    ):
        objs, appearances = data.get_for_diff()
        seq = []
        for obj, appear in zip(objs, appearances):
            seq.append(DiffDumper.ListItem(appear, obj))
        return dumper.represent_data(seq)

    @staticmethod
    def list_item_representer(dumper: yaml.Dumper, data):
        return dumper.represent_scalar(data.tag, data.data)


class MergeDumper(yaml.Dumper):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_representer(ProcessNode, self.class_representer)
        self.add_representer(ConnectionNode, self.class_representer)
        self.add_representer(ConnectionBlock, self.class_representer)
        self.add_representer(IfAllEqList, self.list_representer)
        self.add_representer(WildcardList, self.list_representer)

    @staticmethod
    def class_representer(
        dumper: yaml.Dumper,
        data: Union[ProcessNode, ConnectionNode, ConnectionBlock],
    ):
        return dumper.represent_dict(data.node)

    @staticmethod
    def list_representer(
        dumper: yaml.Dumper, data: Union[IfAllEqList, WildcardList]
    ):
        obj = data.get_for_merge()
        return dumper.represent_data(obj)


current_fingerprint = 0

T2 = TypeVar("T2")


def iter_prints(objs: List[T2]) -> Generator[T2, None, None]:
    global current_fingerprint
    for i, obj in enumerate(objs):
        current_fingerprint = i
        yield obj


spec_fns = {}


def merge_subs(objs, key, ret):
    sub_list = None
    try:
        sub_list = [obj[key].copy() for obj in objs]
    except AttributeError:
        try:
            sub_list = [obj[key] for obj in objs]
        except KeyError:
            return
    except KeyError:
        return
    except Exception:
        print("hi")
    new = None
    if key in spec_fns:
        new = spec_fns[key](sub_list)
    else:
        new = globals()[f"merge_{key}"](sub_list)
    if new is not None:
        ret[key] = new


def wildcard_merge(key):
    def do_wildcard(strs: List[str]):
        ret = WildcardList()
        for string in iter_prints(strs):
            ret.add_str(string)
        return ret

    spec_fns[key] = do_wildcard


def if_all_eq_merge(key):
    def do_if_all_eq(objs: list):
        ret = IfAllEqList()
        for obj in iter_prints(objs):
            ret.add_obj(obj)
        return ret

    spec_fns[key] = do_if_all_eq


def dictionary_mod(fn) -> Dict:
    def wrapper(obj_list, fields: Union[List[str], str] = None) -> Dict:
        ret = dict()
        if fields is not None:
            if isinstance(fields, str):
                fields = [fields]
            fn(obj_list, ret, fields)
        else:
            fn(obj_list, ret)
        return ret

    return wrapper


@dictionary_mod
def merge_objects(
    objects: List[Dict], ret: Dict, fields=[lib.METADATA_FIELD, lib.SPEC_FIELD]
):
    for field in fields:
        merge_subs(objects, field, ret)


@dictionary_mod
def merge_metadata(metadatas, ret):
    merge_subs(metadatas, "name", ret)
    merge_subs(metadatas, "type", ret)


wildcard_merge("name")
if_all_eq_merge("type")


@dictionary_mod
def merge_spec(fingerprints, ret):
    merge_subs(fingerprints, "containerSelector", ret)
    merge_subs(fingerprints, "podSelector", ret)
    merge_subs(fingerprints, "namespaceSelector", ret)
    merge_subs(fingerprints, "serviceSelector", ret)
    merge_subs(fingerprints, "machineSelector", ret)
    merge_subs(fingerprints, "processPolicy", ret)
    merge_subs(fingerprints, "networkPolicy", ret)


def merge_containerSelector(selectors):
    ret = dict()
    merge_subs(selectors, "containerName", ret)
    merge_subs(selectors, "image", ret)
    merge_subs(selectors, "imageID", ret)
    if len(ret) > 0:
        return ret
    return None


wildcard_merge("containerName")
wildcard_merge("image")
if_all_eq_merge("imageID")


@dictionary_mod
def merge_podSelector(selectors, ret):
    merge_subs(selectors, "matchLabels", ret)


@dictionary_mod
def merge_namespaceSelector(selectors, ret):
    merge_subs(selectors, "matchLabels", ret)


@dictionary_mod
def merge_matchLabels(labels, ret):
    merge_subs(labels, "controller-revision-hash", ret)
    merge_subs(labels, "k8s-app", ret)
    merge_subs(labels, "pod-template-generation", ret)
    merge_subs(labels, "kubernetes.io/metadata.name", ret)


if_all_eq_merge("controller-revision-hash")
wildcard_merge("k8s-app")
if_all_eq_merge("pod-template-generation")
wildcard_merge("kubernetes.io/metadata.name")


if_all_eq_merge("serviceSelector")
if_all_eq_merge("machineSelector")


def merge_processPolicy(policies):
    ret: List[ProcessNode] = []
    ProcessID.all_ids = []
    for proc_list in iter_prints(policies):
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


@dictionary_mod
def merge_networkPolicy(profiles, ret):
    merge_subs(profiles, "ingress", ret)
    merge_subs(profiles, "egress", ret)


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
