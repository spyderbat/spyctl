import fnmatch
import ipaddress as ipaddr
import json
import re
import time
from copy import deepcopy
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import yaml

import spyctl.cli as cli
import spyctl.schemas_v2 as schemas
import spyctl.spyctl_lib as lib

SPEC_FIELD = lib.SPEC_FIELD
CONT_SELECTOR_FIELD = lib.CONT_SELECTOR_FIELD
SVC_SELECTOR_FIELD = lib.SVC_SELECTOR_FIELD
POD_SELECTOR_FIELD = lib.POD_SELECTOR_FIELD
MACHINE_SELECTOR_FIELD = lib.MACHINE_SELECTOR_FIELD
NAMESPACE_SELECTOR_FIELD = lib.NAMESPACE_SELECTOR_FIELD
USER_SELECTOR_FIELD = lib.USER_SELECTOR_FIELD
TRACE_SELECTOR_FIELD = lib.TRACE_SELECTOR_FIELD
MATCH_LABELS_FIELD = lib.MATCH_LABELS_FIELD
PROC_POLICY_FIELD = lib.PROC_POLICY_FIELD
NET_POLICY_FIELD = lib.NET_POLICY_FIELD
INGRESS_FIELD = lib.INGRESS_FIELD
EGRESS_FIELD = lib.EGRESS_FIELD
IMAGE_FIELD = lib.IMAGE_FIELD
IMAGEID_FIELD = lib.IMAGEID_FIELD
CONT_NAME_FIELD = lib.CONT_NAME_FIELD
CONT_ID_FIELD = lib.CONT_ID_FIELD
CGROUP_FIELD = lib.CGROUP_FIELD
HOSTNAME_FIELD = lib.HOSTNAME_FIELD
RESPONSE_FIELD = lib.RESPONSE_FIELD

NODE_TYPE_EGRESS = "egress"
NODE_TYPE_INGRESS = "ingress"
DIFF_HEAD = "__DIFF_HEAD__"
DIFF_END = "__DIFF_END__"

BASE_NODE_LIST = None
MERGING_NODE_LIST = None

ADD_START = "+ "
SUB_START = "- "
LIST_MARKER = "- "
DEFAULT_WHITESPACE = "  "
NET_POL_FIELDS = {lib.INGRESS_FIELD, lib.EGRESS_FIELD}
OR_FIELDS = {lib.TO_FIELD, lib.FROM_FIELD}


class InvalidMergeError(Exception):
    pass


class InvalidDiffError(Exception):
    pass


class MergeObject:
    def __init__(
        self,
        obj_data: Dict,
        merge_schemas: List["MergeSchema"],
        validation_fn: Callable,
        merge_network: bool = True,
        disable_procs: str = None,
        disable_conns: str = None,
    ) -> None:
        self.original_obj = deepcopy(obj_data)
        self.obj_data = deepcopy(obj_data)
        self.schemas = merge_schemas
        self.validation_fn = validation_fn
        self.starting_yaml = yaml.dump(obj_data)
        self.merge_network = merge_network
        self.is_guardian = lib.is_guardian_obj(self.original_obj)
        self.irrelevant_objects: Dict[
            str, Set[str]
        ] = {}  # kind -> Set(checksum or id) if checksum missing
        self.relevant_objects: Dict[
            str, Set[str]
        ] = {}  # kind -> Set(checksum or id) if checksum missing
        # guardian spec merge settings
        self.__parse_disable_procs_settings(disable_procs)
        self.__parse_disable_conns_settings(disable_conns)

    def symmetric_merge(self, other: Dict, check_irrelevant=False):
        global BASE_NODE_LIST, MERGING_NODE_LIST
        BASE_NODE_LIST = None
        MERGING_NODE_LIST = None
        if (spec_cp := self.obj_data.get(lib.SPEC_FIELD)) and check_irrelevant:
            spec_cp = deepcopy(self.obj_data[lib.SPEC_FIELD])
        for schema in self.schemas:
            data = self.obj_data.get(schema.field)
            other_data = other.get(schema.field, {})
            if (
                not self.__merge_subfields(
                    data, other_data, schema, symmetric=True
                )
                and schema.field in self.obj_data
            ):
                del self.obj_data[schema.field]
        if spec_cp and check_irrelevant:
            self.check_irrelevant_obj(spec_cp, other)

    def asymmetric_merge(self, other: Dict, check_irrelevant=False):
        global BASE_NODE_LIST, MERGING_NODE_LIST
        BASE_NODE_LIST = None
        MERGING_NODE_LIST = None
        if (spec_cp := self.obj_data.get(lib.SPEC_FIELD)) and check_irrelevant:
            spec_cp = deepcopy(self.obj_data[lib.SPEC_FIELD])
        for schema in self.schemas:
            data = self.obj_data.get(schema.field)
            other_data = other.get(schema.field, {})
            if (
                not self.__merge_subfields(data, other_data, schema)
                and schema.field in self.obj_data
            ):
                del self.obj_data[schema.field]
        if spec_cp and check_irrelevant:
            self.check_irrelevant_obj(spec_cp, other)

    def is_valid_obj(self) -> bool:
        try:
            self.validation_fn(self.obj_data)
            return True
        except Exception as e:
            cli.try_log(f"Merge created invalid object. {' '.join(e.args)}")
            return False

    def check_irrelevant_obj(self, spec_cp: Dict, other: Dict):
        checksum_or_id = self.__get_checksum_or_id(other)
        other_kind = other[lib.KIND_FIELD]
        if (
            other_kind in self.relevant_objects
            and checksum_or_id in self.relevant_objects[other_kind]
        ):
            return
        if self.obj_data[lib.SPEC_FIELD] == spec_cp:
            self.irrelevant_objects.setdefault(other_kind, set())
            self.irrelevant_objects[other_kind].add(checksum_or_id)
        else:
            self.relevant_objects.setdefault(other_kind, set())
            self.relevant_objects[other_kind].add(checksum_or_id)

    def get_irrelevant_objects(self) -> Dict[str, Set[str]]:
        return {k: list(v) for k, v in self.irrelevant_objects.items()}

    def is_relevant_obj(self, other_kind: str, other: Union[Dict, str]):
        if isinstance(other, str):
            return other in self.relevant_objects.get(other_kind, set())
        else:
            checksum_or_id = self.__get_checksum_or_id(other)
            return checksum_or_id in self.relevant_objects.get(
                other_kind, set()
            )

    def __get_checksum_or_id(self, other: Dict) -> str:
        rv = other[lib.METADATA_FIELD].get(lib.CHECKSUM_FIELD)
        if not rv:
            rv = other[lib.METADATA_FIELD][lib.METADATA_UID_FIELD]
        return rv

    @property
    def is_valid(self) -> bool:
        return schemas.valid_object(self.obj_data)

    def get_diff(
        self, full_diff=False, diff_object=False
    ) -> Optional[Union[str, Dict]]:
        if diff_object and self.is_guardian:
            return guardian_object_diff(self.original_obj, self.obj_data)
        else:
            original_yaml: str = yaml.dump(self.original_obj, sort_keys=False)
            yaml_lines = original_yaml.splitlines()
            diff_all_fields(self.original_obj, self.obj_data, yaml_lines)
            if full_diff:
                return "\n".join(yaml_lines)
            else:
                summary = []
                in_sum = set()
                found_spec = False

                def add_line_to_sum(index, sum_line):
                    if index not in in_sum:
                        if (
                            index != 0
                            and index - 1 >= 0
                            and index - 1 not in in_sum
                        ):
                            summary.append("...")
                        summary.append(sum_line)
                        in_sum.add(index)

                for i, line in enumerate(yaml_lines):
                    stripped = line.strip()
                    if (
                        line.startswith(f"{lib.ADD_COLOR}{ADD_START}")
                        or line.startswith(f"{ADD_START}")
                        or line.startswith(f"{lib.SUB_COLOR}{SUB_START}")
                        or line.startswith(f"{SUB_START}")
                        or not found_spec
                        or stripped.startswith(lib.PROC_POLICY_FIELD)
                        or stripped.startswith(lib.NET_POLICY_FIELD)
                        or stripped.startswith(lib.INGRESS_FIELD)
                        or stripped.startswith(lib.EGRESS_FIELD)
                    ):
                        if line.strip().startswith(lib.SPEC_FIELD):
                            found_spec = True
                        for x in range(i - 5, i):
                            if x >= 0:
                                add_line_to_sum(x, yaml_lines[x])
                        add_line_to_sum(i, line)
                        for x in range(i + 1, i + 6):
                            if x < len(yaml_lines):
                                add_line_to_sum(x, yaml_lines[x])
                if max(in_sum) != len(yaml_lines) - 1:
                    summary.append("...")
                return "\n".join(summary)

    def get_obj_data(self):
        return self.obj_data

    def update_latest_timestamp(self, timestamp=None):
        meta = self.obj_data.get(lib.METADATA_FIELD)
        if meta and lib.LATEST_TIMESTAMP_FIELD in meta:
            if timestamp:
                meta[lib.LATEST_TIMESTAMP_FIELD] = timestamp
            else:
                meta[lib.LATEST_TIMESTAMP_FIELD] = time.time()

    def __merge_subfields(
        self,
        data: Optional[Dict],
        other_data: Optional[Dict],
        schema: "MergeSchema",
        symmetric=False,
    ) -> bool:
        for field, func in schema.merge_functions.items():
            f_data = data.get(field) if data is not None else None
            f_other_data = (
                other_data.get(field) if other_data is not None else None
            )
            result = self.__handle_merge_functions(
                f_data, f_other_data, func, symmetric
            )
            if result is None and data and field in data:
                del data[field]
            elif result is not None:
                data[field] = result
        for field, sub_schema in schema.sub_schemas.items():
            if field != sub_schema.field:
                raise InvalidMergeError(
                    "Bug Detected! Field mismatch with field in sub schema."
                )
            f_data = data.get(field) if data is not None else None
            f_other_data = (
                other_data.get(field) if other_data is not None else None
            )
            if symmetric:
                if f_data is None and f_other_data is None:
                    continue
                elif (
                    f_data is None or f_other_data is None
                ) and sub_schema.is_selector:
                    if field in data:
                        del data[field]
                    continue
                elif f_data is None:
                    data[field] = f_other_data
                elif f_other_data is None:
                    continue
                else:
                    if (
                        not self.__merge_subfields(
                            f_data, f_other_data, sub_schema, symmetric
                        )
                        and field in data
                    ):
                        del data[field]
            else:
                if f_data is None or f_other_data is None:
                    continue
                else:
                    if (
                        not self.__merge_subfields(
                            f_data, f_other_data, sub_schema, symmetric
                        )
                        and field in data
                    ):
                        del data[field]
        # Clear any fields not found in the schema
        valid_fields = set(schema.merge_functions).union(
            set(schema.sub_schemas)
        )
        if data:
            for field in set(data) - valid_fields:
                del data[field]
        if schema.values_required and not data:
            return False
        else:
            return True

    def __handle_merge_functions(
        self, data: Any, other_data: Any, func: Callable, symmetric: bool
    ):
        if not self.merge_network and func == merge_ingress_or_egress:
            return data
        if symmetric:
            if data is None or other_data is None:
                result = None
            else:
                result = func(self, data, other_data, symmetric)
        else:
            if data is None and other_data is None:
                result = None
            if data is None:
                result = None
            if other_data is None:
                result = data
            else:
                result = func(self, data, other_data, symmetric)
        return result

    def __parse_disable_procs_settings(self, s: str) -> bool:
        dpf = self.original_obj.get(lib.SPEC_FIELD, {}).get(
            lib.DISABLE_PROCS_FIELD, ""
        )
        if s == lib.DISABLE_PROCS_ALL or dpf == lib.DISABLE_PROCS_ALL:
            self.disable_procs = lib.DISABLE_PROCS_ALL
        else:
            self.disable_procs = None

    def __parse_disable_conns_settings(self, s: str) -> bool:
        dcf = self.original_obj.get(lib.SPEC_FIELD, {}).get(
            lib.DISABLE_CONNS_FIELD, ""
        )
        if s == lib.DISABLE_CONNS_ALL or dcf == lib.DISABLE_CONNS_ALL:
            self.disable_conns = lib.DISABLE_CONNS_ALL
        elif s == lib.DISABLE_CONNS_EGRESS or dcf == lib.EGRESS_FIELD:
            self.disable_conns = lib.EGRESS_FIELD
        elif s == lib.DISABLE_CONNS_INGRESS or dcf == lib.INGRESS_FIELD:
            self.disable_conns = lib.INGRESS_FIELD
        else:
            self.disable_conns = None

        dpr = self.original_obj.get(lib.SPEC_FIELD, {}).get(
            lib.DISABLE_PR_CONNS_FIELD, ""
        )
        if s == lib.DISABLE_CONNS_PRIVATE or dpr == lib.DISABLE_CONNS_ALL:
            self.disable_private_conns = lib.DISABLE_CONNS_ALL
        elif s == lib.DISABLE_CONNS_PRIVATE_E or dpr == lib.EGRESS_FIELD:
            self.disable_private_conns = lib.EGRESS_FIELD
        elif s == lib.DISABLE_CONNS_PRIVATE_I or dpr == lib.INGRESS_FIELD:
            self.disable_private_conns = lib.INGRESS_FIELD
        else:
            self.disable_private_conns = None

        dpu = self.original_obj.get(lib.SPEC_FIELD, {}).get(
            lib.DISABLE_PU_CONNS_FIELD, ""
        )
        if s == lib.DISABLE_CONNS_PUBLIC or dpu == lib.DISABLE_CONNS_ALL:
            self.disable_public_conns = lib.DISABLE_CONNS_ALL
        elif s == lib.DISABLE_CONNS_PUBLIC_E or dpu == lib.EGRESS_FIELD:
            self.disable_public_conns = lib.EGRESS_FIELD
        elif s == lib.DISABLE_CONNS_PUBLIC_I or dpu == lib.INGRESS_FIELD:
            self.disable_public_conns = lib.INGRESS_FIELD
        else:
            self.disable_public_conns = None


class MergeSchema:
    def __init__(
        self,
        field: str,
        sub_schemas: Dict[str, "MergeSchema"] = {},
        merge_functions: Dict[str, Callable] = {},
        values_required=False,
        is_selector=False,
    ) -> None:
        self.field = field
        self.sub_schemas = sub_schemas
        self.merge_functions = merge_functions
        self.values_required = values_required
        # Flag required because selectors behave differently
        # Each item in the merge must have at least one thing
        # in common for a given selector or that selector will remain
        # deleted.
        self.is_selector = is_selector


class ProcessNode:
    def __init__(
        self,
        node_list: "ProcessNodeList",
        node_data: Dict,
        eusers=[],
        parent=None,
    ) -> None:
        self.node = node_data.copy()
        self.name = node_data[lib.NAME_FIELD]
        self.id = node_data[lib.ID_FIELD]
        self.merged_id = None  # New id if merged
        self.exes: List[str] = node_data[lib.EXE_FIELD]
        self.eusers: List[str] = self.node.get(lib.EUSER_FIELD, eusers)
        self.node_list = node_list
        self.parent = parent
        self.children = []
        self.listening_sockets: List["PortRange"] = []
        self.__parse_listening_sockets()
        if lib.CHILDREN_FIELD in self.node:
            self.children = [
                child[lib.ID_FIELD] for child in self.node[lib.CHILDREN_FIELD]
            ]

    def symmetrical_merge(self, other_node: "ProcessNode"):
        self.name = make_wildcard([self.name, other_node.name])
        self.__merge_exes(other_node.exes)
        self.__merge_eusers(other_node.eusers)
        self.__merge_listening_socks(other_node.listening_sockets)
        other_node.merged_id = self.id

    def asymmetrical_merge(self, other_node: "ProcessNode"):
        if not fnmatch.fnmatch(other_node.name, self.name):
            raise InvalidMergeError("Bug detected, name mismatch in merge.")
        self.__merge_exes(other_node.exes)
        self.__merge_eusers(other_node.eusers)
        self.__merge_listening_socks(other_node.listening_sockets)
        other_node.merged_id = self.id

    def as_dict(self, parent_eusers: List[str] = None) -> Dict:
        rv = {}
        rv[lib.NAME_FIELD] = self.name
        rv[lib.EXE_FIELD] = sorted(self.exes)
        rv[lib.ID_FIELD] = self.id
        if parent_eusers and set(parent_eusers) != set(self.eusers):
            rv[lib.EUSER_FIELD] = sorted(self.eusers)
        elif not parent_eusers:
            rv[lib.EUSER_FIELD] = sorted(self.eusers)
        if self.listening_sockets:
            rv[lib.LISTENING_SOCKETS] = sorted(
                [l_sock.as_dict() for l_sock in self.listening_sockets],
                key=lambda d: d[lib.PORT_FIELD],
            )
        if len(self.children) > 0:
            child_nodes = [
                self.node_list.get_node(c_id) for c_id in self.children
            ]
            rv[lib.CHILDREN_FIELD] = [
                n.as_dict(self.eusers) for n in child_nodes
            ]
            rv[lib.CHILDREN_FIELD].sort(key=lambda x: x[lib.NAME_FIELD])
        return rv

    def symmetrical_in(self, other) -> bool:
        if isinstance(other, __class__):
            if not self.__match_exes(other.exes):
                return False
            wildcard_name = make_wildcard([self.name, other.name])
            if (
                not fnmatch.fnmatch(other.name, self.name)
                and not wildcard_name
            ):
                return False
            return True
        return False

    def __parse_listening_sockets(self):
        socket_list = self.node.get(lib.LISTENING_SOCKETS)
        if socket_list:
            for sock in socket_list:
                port = sock[lib.PORT_FIELD]
                proto = sock[lib.PROTO_FIELD]
                endport = sock.get(lib.ENDPORT_FIELD)
                self.listening_sockets.append(PortRange(port, proto, endport))

    def __contains__(self, other):
        if isinstance(other, __class__):
            if not fnmatch.fnmatch(other.name, self.name):
                return False
            if not self.__match_exes(other.exes):
                return False
            return True
        return False

    def __eq__(self, other):
        if isinstance(other, __class__):
            if not (
                fnmatch.fnmatch(other.name, self.name)
                or fnmatch.fnmatch(self.name, other.name)
            ):
                return False
            if not self.__match_exes(
                other.exes, strict=True, single_match=True
            ):
                return False
            if not self.__match_eusers(other.eusers):
                return False
            if not self.__match_listening_socks(other.listening_sockets):
                return False
            return True
        return False

    def __match_exe(self, other_exe: List[str], strict=False) -> bool:
        if other_exe in self.exes:
            return True
        other_name = Path(other_exe).name
        for exe in self.exes:
            if fnmatch.fnmatch(other_exe, exe):
                return True
            if not strict:
                exe_name = Path(exe).name
                if fnmatch.fnmatch(other_name, exe_name):
                    return True
        return False

    def __match_exes(
        self, other_exes: str, strict=False, single_match=False
    ) -> bool:
        match = False
        for other_exe in other_exes:
            if single_match:
                if self.__match_exe(other_exe, strict):
                    match = True
                    break
            if not self.__match_exe(other_exe, strict):
                return False
        # For symmetrical in, we only care if two processes share at least one
        # overlapping exe, hence the single match logic.
        if single_match and not match:
            return False
        return True

    def __match_euser(self, other_euser: str):
        if other_euser in self.eusers:
            return True
        for euser in self.eusers:
            if fnmatch.fnmatch(other_euser, euser):
                return True
        return False

    def __match_eusers(self, other_eusers: List[str]) -> bool:
        for other_euser in other_eusers:
            if not self.__match_euser(other_euser):
                return False
        return True

    def __match_listening_sock(self, other_sock: "PortRange") -> bool:
        for sock in self.listening_sockets:
            if other_sock in sock:
                return True
        return False

    def __match_listening_socks(self, other_socks: List["PortRange"]) -> bool:
        for o_sock in other_socks:
            if not self.__match_listening_sock():
                return False
        return True

    def __merge_exes(self, other_exes: List[str]):
        for other_exe in other_exes:
            match = False
            if other_exe not in self.exes:
                for exe in self.exes:
                    if fnmatch.fnmatch(other_exe, exe):
                        match = True
                        break
                if not match:
                    self.exes.append(other_exe)

    def __merge_eusers(self, other_eusers: List[str]):
        for other_euser in other_eusers:
            if other_euser not in self.eusers:
                self.eusers.append(other_euser)

    def __contains_socket(self, o_sock: "PortRange"):
        for sock in self.listening_sockets:
            if o_sock in sock:
                return True
        return False

    def __merge_listening_socks(self, other_socks: List["PortRange"]):
        for o_sock in other_socks:
            if not self.__contains_socket(o_sock):
                self.listening_sockets.append(o_sock)


class ProcessNodeList:
    def __init__(self, nodes_data: List[Dict]) -> None:
        self.proc_nodes: Dict[str, ProcessNode] = {}  # id > ProcessNode
        self.proc_name_index: Dict[str, List[str]] = {}
        self.roots: List[ProcessNode] = []
        self.ids = set()
        # Node lists from deviations or suggestions may
        # be treated differently in some cases
        self.dev_or_sug = False
        for node_data in nodes_data:
            root_node = self.__add_node(node_data)
            if len(root_node.eusers) == 0:
                raise InvalidMergeError("Root process has no eusers")
            self.roots.append(root_node)

    def get_node(self, id: str) -> Optional[ProcessNode]:
        return self.proc_nodes.get(id)

    def symmetrical_merge(self, other_list: "ProcessNodeList"):
        for other_node in other_list.roots:
            match = False
            for node in self.roots:
                if node.symmetrical_in(
                    other_node
                ) or other_node.symmetrical_in(node):
                    match = True
                    break
            if match:
                node.symmetrical_merge(other_node)
                self.__symmetrical_merge_helper(node, other_node)
            else:
                self.__add_merged_root(other_node)

    def asymmetrical_merge(self, other_list: "ProcessNodeList"):
        for other_node in other_list.roots:
            match = False
            for node in self.roots:
                if other_node in node:
                    match = True
                    break
            if match:
                node.asymmetrical_merge(other_node)
                self.__asymmetrical_merge_helper(node, other_node)
            else:
                self.__add_merged_root(other_node)

    def get_data(self) -> List[Dict]:
        rv = []
        for node in self.roots:
            rv.append(node.as_dict())
        return rv

    def __unique_id(self, curr_id: str) -> str:
        if curr_id not in self.ids:
            return curr_id
        new_id = curr_id
        while new_id in self.ids:
            id_parts = new_id.split("_")
            if len(id_parts) > 1 and id_parts[-1].isdigit():
                id_parts[-1] = str(int(id_parts[-1]) + 1)
                new_id = "_".join(id_parts)
            else:
                id_parts.append("0")
                new_id = "_".join(id_parts)
        return new_id

    def __symmetrical_merge_helper(
        self, node: ProcessNode, other_node: ProcessNode
    ):
        for o_child_id in other_node.children:
            match = False
            o_child_node = other_node.node_list.get_node(o_child_id)
            if not o_child_node:
                raise InvalidMergeError("Bug, node list missing ID")
            for child_id in node.children:
                child_node = self.get_node(child_id)
                if not child_node:
                    raise InvalidMergeError("Bug, node list missing ID")
                if child_node.symmetrical_in(
                    o_child_node
                ) or o_child_node.symmetrical_in(child_node):
                    match = True
                    break
            if match:
                child_node.symmetrical_merge(o_child_node)
                self.__symmetrical_merge_helper(child_node, o_child_node)
            else:
                self.__add_merged_subtree(o_child_node, node)

    def __asymmetrical_merge_helper(
        self, node: ProcessNode, other_node: ProcessNode
    ):
        for o_child_id in other_node.children:
            match = False
            o_child_node = other_node.node_list.get_node(o_child_id)
            if not o_child_node:
                raise InvalidMergeError("Bug, node list missing ID")
            for child_id in node.children:
                child_node = self.get_node(child_id)
                if not child_node:
                    raise InvalidMergeError("Bug, node list missing ID")
                if o_child_node in child_node:
                    match = True
                    break
            if match:
                child_node.asymmetrical_merge(o_child_node)
                self.__asymmetrical_merge_helper(child_node, o_child_node)
            else:
                self.__add_merged_subtree(o_child_node, node)
        pass

    def __add_node(
        self, node_data: Dict, eusers=[], parent=None
    ) -> "ProcessNode":
        if "policyNode" in node_data:
            self.dev_or_sug = True
            id = node_data["policyNode"]["id"]
            children = node_data["policyNode"].get(lib.CHILDREN_FIELD)
            if id not in BASE_NODE_LIST.ids:
                raise InvalidMergeError(
                    f"Deviation process node ID ({id}) is missing in base"
                    " policy"
                )
            node = BASE_NODE_LIST.get_node(id)
            node_data = node.node.copy()
            node_data.pop(lib.CHILDREN_FIELD, None)
            if children:
                node_data[lib.CHILDREN_FIELD] = children
            while node.parent:
                parent = BASE_NODE_LIST.get_node(node.parent)
                parent_data = parent.node.copy()
                parent_data[lib.CHILDREN_FIELD] = [node_data]
                node_data = parent_data
                node = parent
        proc_node = ProcessNode(self, node_data, eusers, parent)
        self.proc_nodes[proc_node.id] = proc_node
        self.proc_name_index.setdefault(proc_node.name, [])
        self.proc_name_index[proc_node.name].append(proc_node.id)
        if proc_node.id in self.ids:
            if not self.dev_or_sug:
                raise InvalidMergeError(
                    f"Duplicate process id detected. ({proc_node.id})"
                )
            else:
                # deviations or suggestions can have ids that already exist in
                # the base policy, so we need to generate a new id for the
                # deviation
                new_id = self.__unique_id(proc_node.id)
                proc_node.id = new_id
        self.ids.add(proc_node.id)
        for child_data in node_data.get(lib.CHILDREN_FIELD, []):
            self.__add_node(child_data, proc_node.eusers, proc_node.id)
        return proc_node

    def __add_merged_root(self, other_node: ProcessNode):
        root_node = self.__add_merged_node(other_node, other_node.eusers)
        if len(root_node.eusers) == 0:
            raise InvalidMergeError("Root process has no eusers")
        self.roots.append(root_node)

    def __add_merged_subtree(
        self, other_node: ProcessNode, parent_node: ProcessNode
    ):
        sub_tree_root = self.__add_merged_node(
            other_node, other_node.eusers, parent_node.id
        )
        parent_node.children.append(sub_tree_root.id)

    def __add_merged_node(
        self, other_node: ProcessNode, eusers=[], parent=None
    ) -> ProcessNode:
        proc_node = ProcessNode(self, other_node.node, eusers, parent)
        if proc_node.id in self.ids:
            new_id = self.__unique_id(proc_node.id)
            proc_node.id = new_id
        other_node.merged_id = proc_node.id
        self.proc_nodes[proc_node.id] = proc_node
        self.proc_name_index.setdefault(proc_node.name, [])
        self.proc_name_index[proc_node.name].append(proc_node.id)
        self.ids.add(proc_node.id)
        if lib.CHILDREN_FIELD in proc_node.node:
            new_children_ids = []
            for child_data in proc_node.node.get(lib.CHILDREN_FIELD):
                child_id = child_data[lib.ID_FIELD]
                child_node = other_node.node_list.get_node(child_id)
                if not child_node:
                    raise InvalidMergeError("Bug, node list missing ID")
                added_child = self.__add_merged_node(
                    child_node, proc_node.eusers, proc_node.id
                )
                new_children_ids.append(added_child.id)
            proc_node.children = new_children_ids
        return proc_node


class InvalidNetworkNode(Exception):
    pass


class IPBlock:
    def __init__(
        self,
        ip_network: Union[ipaddr.IPv4Network, ipaddr.IPv6Network],
        except_networks: List = None,
    ) -> None:
        self.network = ip_network
        self.except_networks = except_networks
        if except_networks is not None:
            for net in except_networks:
                if not ip_network.supernet_of(net):
                    raise InvalidNetworkNode(
                        "Except block must be completely within cidr network"
                    )

    def as_dict(self) -> Dict:
        ipblock_dict = {lib.CIDR_FIELD: str(self.network)}
        if self.except_networks:
            ipblock_dict[lib.EXCEPT_FIELD] = [
                str(net) for net in self.except_networks
            ]
        rv = {lib.IP_BLOCK_FIELD: ipblock_dict}
        return rv

    def __contains__(self, other):
        if isinstance(other, IPBlock):
            if self.except_networks is not None:
                for net in self.except_networks:
                    try:
                        if net.supernet_of(other.network):
                            return False
                    except TypeError:
                        # Occurs when comparing ipv4 with ipv6
                        continue
            try:
                if self.network.supernet_of(other.network):
                    return True
            except TypeError:
                return False
        return False

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, IPBlock):
            return False
        return (
            self.network == __o.network
            and self.except_networks == __o.except_networks
        )


class PortRange:
    def __init__(self, port: int, proto: str, endport: int = None) -> None:
        self.port = port
        self.proto = proto
        self.endport = endport if endport is not None else self.port
        if self.endport < self.port:
            raise InvalidNetworkNode(
                f"The {lib.ENDPORT_FIELD} value must be greater than or equal"
                f" to {lib.PORT_FIELD} value."
            )

    def as_dict(self) -> Dict:
        rv = {lib.PROTO_FIELD: self.proto, lib.PORT_FIELD: self.port}
        if self.endport != self.port:
            rv[lib.ENDPORT_FIELD] = self.endport
        return rv

    def __contains__(self, other):
        if isinstance(other, PortRange):
            if (
                self.port <= other.port <= self.endport
                and self.port <= other.endport <= self.endport
                and self.proto == other.proto
            ):
                return True
        return False


class NetworkNode:
    def __init__(
        self,
        node_list: "NetworkNodeList",
        node_data: Dict,
        proc_node_list: ProcessNodeList,
    ) -> None:
        self.ip_blocks: List[IPBlock] = []
        self.proc_node_list = proc_node_list
        self.dns_names = []
        self.port_ranges: List[PortRange] = []
        self.processes = node_data.get(lib.PROCESSES_FIELD, [])
        self.node_list = node_list
        # Anded blocks are not supported
        self.anded_blocks = []
        if lib.TO_FIELD in node_data:
            self.type = NODE_TYPE_EGRESS
            self.__parse_or_blocks(node_data[lib.TO_FIELD])
        elif lib.FROM_FIELD in node_data:
            self.type = NODE_TYPE_INGRESS
            self.__parse_or_blocks(node_data[lib.FROM_FIELD])
        else:
            raise InvalidNetworkNode(
                f"Missing {lib.TO_FIELD} or {lib.FROM_FIELD} field."
            )
        self.__parse_port_block(node_data[lib.PORTS_FIELD])

    def symmetrical_merge(
        self,
        other_node: "NetworkNode",
    ):
        self.__merge_ip_blocks(
            other_node.ip_blocks,
            symmetrical=True,
        )
        self.__merge_dns_names(
            other_node.dns_names,
            symmetrical=True,
        )
        self.__merge_process_ids(other_node.processes)

    def asymmetrical_merge(self, other_node: "NetworkNode"):
        self.__merge_ip_blocks(
            other_node.ip_blocks,
            symmetrical=False,
        )
        self.__merge_dns_names(
            other_node.dns_names,
            symmetrical=False,
        )
        self.__merge_process_ids(other_node.processes)

    def internal_merge(self):
        if self.node_list.ignore_procs:
            self.proc_node_list = []
        new_blocks = []
        for i, block in enumerate(self.ip_blocks):
            if any([block in nb for nb in new_blocks]):
                continue
            if self.node_list.ignore_private and block.network.is_private:
                continue
            if self.node_list.ignore_public and not block.network.is_private:
                continue
            next_index = i + 1
            if any([block in ob for ob in self.ip_blocks[next_index:]]):
                continue
            new_blocks.append(block)
        self.ip_blocks = new_blocks
        dns_names = set()
        for dns_name in self.dns_names:
            if self.node_list.ignore_private and lib.is_private_dns(dns_name):
                continue
            if self.node_list.ignore_public and lib.is_public_dns(dns_name):
                continue
            dns_names.add(dns_name)
        self.dns_names = list(dns_names)

    def as_dict(self) -> Optional[Dict]:
        or_field_string = (
            lib.TO_FIELD if self.type == NODE_TYPE_EGRESS else lib.FROM_FIELD
        )
        rv = {}
        dns_names = [
            {lib.DNS_SELECTOR_FIELD: [name]} for name in sorted(self.dns_names)
        ]
        ipv4_blocks = [
            b
            for b in self.ip_blocks
            if isinstance(b.network, ipaddr.IPv4Network)
        ]
        ipv4_blocks.sort(key=lambda x: x.network)
        ipv4_blocks = [b.as_dict() for b in ipv4_blocks]
        ipv6_blocks = [
            b
            for b in self.ip_blocks
            if isinstance(b.network, ipaddr.IPv6Network)
        ]
        ipv6_blocks.sort(key=lambda x: x.network)
        ipv6_blocks = [b.as_dict() for b in ipv6_blocks]
        or_blocks = dns_names + ipv4_blocks + ipv6_blocks
        if not or_blocks:
            return None
        rv[or_field_string] = or_blocks
        if self.processes:
            rv[lib.PROCESSES_FIELD] = self.processes
        rv[lib.PORTS_FIELD] = [p.as_dict() for p in self.port_ranges]
        return rv

    @property
    def converted(self) -> "NetworkNode":
        """Makes a copy of self and updates the process ids of the
        copy to the merged ids if this node has been merged.
        Used in symmetrical merges.

        Returns:
            NetworkNode: a converted copy of this network node
        """
        rv = deepcopy(self)
        if self.node_list.ignore_procs:
            rv.processes = []
        else:
            for i, id in enumerate(rv.processes.copy()):
                proc_node = rv.__find_proc_node(id, self.proc_node_list)
                if proc_node is None:
                    raise InvalidNetworkNode(
                        "Unable to find process node to convert"
                    )
                if proc_node.merged_id is not None:
                    rv.processes[i] = proc_node.merged_id
            rv.processes = list(set(rv.processes))
        rv.proc_node_list = BASE_NODE_LIST
        return rv

    def __parse_or_blocks(self, or_blocks: List[Dict]):
        for block in or_blocks:
            if lib.IP_BLOCK_FIELD in block and lib.DNS_SELECTOR_FIELD in block:
                cli.try_log(
                    "Warning: Anded blocks not yet supported. Separate ipBlock"
                    " and dnsSelector into their own list items. Skipping this"
                    " block.."
                )
                continue
            elif lib.IP_BLOCK_FIELD in block:
                ip_block = block[lib.IP_BLOCK_FIELD]
                try:
                    ip_network = ipaddr.IPv4Network(ip_block[lib.CIDR_FIELD])
                    except_block = ip_block.get(lib.EXCEPT_FIELD)
                    except_networks = []
                    if except_block:
                        for except_cidr in except_block:
                            except_net = ipaddr.IPv4Network(except_cidr)
                            except_networks.append(except_net)
                except ipaddr.AddressValueError:
                    try:
                        ip_network = ipaddr.IPv6Network(
                            ip_block[lib.CIDR_FIELD]
                        )
                        except_block = ip_block.get(lib.EXCEPT_FIELD)
                        except_networks = []
                        if except_block:
                            for except_cidr in except_block:
                                except_net = ipaddr.IPv6Network(except_cidr)
                                except_networks.append(except_net)
                    except ipaddr.AddressValueError:
                        raise InvalidNetworkNode("Invalid IP block.")
                block = IPBlock(ip_network, except_networks)
                # Prevent duplicates
                if block not in self.ip_blocks:
                    self.ip_blocks.append(block)
            elif lib.DNS_SELECTOR_FIELD in block:
                for dns_name in block[lib.DNS_SELECTOR_FIELD]:
                    self.dns_names.append(dns_name)

    def __parse_port_block(self, port_block: List[Dict]):
        for port in port_block:
            self.port_ranges.append(
                PortRange(
                    port[lib.PORT_FIELD],
                    port[lib.PROTO_FIELD],
                    port.get(lib.ENDPORT_FIELD),
                )
            )

    def __merge_process_ids(self, other_processes: List[str]):
        if self.node_list.ignore_procs:
            self.processes = []
            return
        self.processes.extend(other_processes)
        self.processes = sorted(list(set(self.processes)))

    def __merge_ip_block(
        self,
        other_ip_block: IPBlock,
        symmetrical=False,
    ):
        if symmetrical:
            match = False
            for i, ip_block in enumerate(self.ip_blocks):
                if other_ip_block in ip_block:
                    match = True
                    break
                elif ip_block in other_ip_block:
                    self.ip_blocks[i] = other_ip_block
                    match = True
                    break
            if not match:
                self.ip_blocks.append(other_ip_block)
        else:
            match = False
            for ip_block in self.ip_blocks:
                if other_ip_block in ip_block:
                    match = True
                    break
            if not match:
                self.ip_blocks.append(other_ip_block)

    def __merge_ip_blocks(
        self,
        other_ip_blocks: List[IPBlock],
        symmetrical=False,
    ):
        for o_ip_block in other_ip_blocks:
            if self.node_list.ignore_private and o_ip_block.network.is_private:
                continue
            if (
                self.node_list.ignore_public
                and not o_ip_block.network.is_private
            ):
                continue
            self.__merge_ip_block(o_ip_block, symmetrical)

    def __merge_dns_name(
        self,
        other_dns_name: str,
        symmetrical=False,
    ):
        if symmetrical:
            match = False
            for i, dns_name in enumerate(self.dns_names):
                if fnmatch.fnmatch(other_dns_name, dns_name):
                    match = True
                    break
                elif fnmatch.fnmatch(dns_name, other_dns_name):
                    match = True
                    self.dns_names[i] = other_dns_name
                    break
            if not match:
                self.dns_names.append(other_dns_name)
        else:
            match = False
            for dns_name in self.dns_names:
                if fnmatch.fnmatch(other_dns_name, dns_name):
                    match = True
                    break
            if not match:
                self.dns_names.append(other_dns_name)

    def __merge_dns_names(
        self,
        other_dns_names: List[str],
        symmetrical=False,
    ):
        for o_dns_name in other_dns_names:
            if self.node_list.ignore_private and lib.is_private_dns(
                o_dns_name
            ):
                continue
            if self.node_list.ignore_public and lib.is_public_dns(o_dns_name):
                continue
            self.__merge_dns_name(o_dns_name, symmetrical)

    def __find_proc_node(
        self, proc_id, node_list: ProcessNodeList
    ) -> Optional[ProcessNode]:
        return node_list.get_node(proc_id)

    def __contains_ip_block(self, other_ip_block: IPBlock) -> bool:
        for ip_block in self.ip_blocks:
            if other_ip_block in ip_block:
                return True
        return False

    def __contains_ip_blocks(self, other_ip_blocks: List[IPBlock]) -> bool:
        for o_ip_block in other_ip_blocks:
            if self.node_list.ignore_private and o_ip_block.network.is_private:
                continue
            if (
                self.node_list.ignore_public
                and not o_ip_block.network.is_private
            ):
                continue
            if not self.__contains_ip_block(o_ip_block):
                return False
        return True

    def __contains_port_range(self, other_port_range: PortRange) -> bool:
        for port_range in self.port_ranges:
            if other_port_range in port_range:
                return True
        return False

    def __contains_port_ranges(
        self, other_port_ranges: List[PortRange]
    ) -> bool:
        for o_port_range in other_port_ranges:
            if not self.__contains_port_range(o_port_range):
                return False
        return True

    def __contains_dns_name(self, other_dns_name: str) -> bool:
        for dns_name in self.dns_names:
            if fnmatch.fnmatch(other_dns_name, dns_name):
                return True
        return False

    def __contains_dns_names(self, other_dns_names: List[str]) -> bool:
        for o_dns_name in other_dns_names:
            if self.node_list.ignore_private and lib.is_private_dns(
                o_dns_name
            ):
                continue
            if self.node_list.ignore_public and lib.is_public_dns(o_dns_name):
                continue
            if not self.__contains_dns_name(o_dns_name):
                return False
        return True

    def __contains_process(
        self, other_process_id: str, other_proc_list: ProcessNodeList
    ) -> bool:
        other_node = self.__find_proc_node(other_process_id, other_proc_list)
        if other_node is None:
            raise InvalidNetworkNode("Unable to find process node")
        # First check if the IDs are a match
        cmp_id = other_node.id
        if other_node.merged_id is not None:
            cmp_id = other_node.merged_id
        if cmp_id in self.processes:
            return True
        # If not a match check that the processes are comparable
        # Here we disregard place in the process tree and we're
        # just looking for processes with the same name and exes
        for node_id in self.processes:
            node = self.proc_node_list.get_node(node_id)
            if other_node in node or node in other_node:
                return True
        return False

    def __contains_processes(
        self, other_processes: List[str], other_proc_list: ProcessNodeList
    ) -> bool:
        if len(self.processes) == 0 or self.node_list.ignore_procs:
            # processes of len 0 means any process
            return True
        for o_process_id in other_processes:
            if not self.__contains_process(o_process_id, other_proc_list):
                return False
        return True

    def __contains__(self, other):
        if isinstance(other, NetworkNode):
            if self.type != other.type:
                return False
            if not self.__contains_port_ranges(other.port_ranges):
                return False
            if len(self.port_ranges) > 1 or len(other.port_ranges) > 1:
                # Assuming stricter conditions when multiple port ranges
                # are involved given that additional ports likely means
                # different services
                if not self.__contains_ip_blocks(other.ip_blocks):
                    return False
                if not self.__contains_dns_names(other.dns_names):
                    return False
            if not self.__contains_processes(
                other.processes, other.proc_node_list
            ):
                return False
            return True
        return False

    def __eq__(self, other):
        if isinstance(other, NetworkNode):
            if self.type != other.type:
                return False
            if not self.__contains_port_ranges(other.port_ranges):
                return False
            if not self.__contains_ip_blocks(other.ip_blocks):
                return False
            if not self.__contains_dns_names(other.dns_names):
                return False
            if not self.__contains_processes(
                other.processes, other.proc_node_list
            ):
                return False
            return True
        return False


class NetworkNodeList:
    def __init__(
        self,
        nodes_data: List[Dict],
        proc_node_list: ProcessNodeList,
        ignore_private=False,
        ignore_public=False,
        ignore_procs=False,
    ) -> None:
        self.nodes: List[NetworkNode] = []
        self.proc_node_list = proc_node_list
        self.ignore_private = ignore_private
        self.ignore_public = ignore_public
        self.ignore_procs = ignore_procs
        for node_data in nodes_data:
            self.__add_node(node_data)
        if self.nodes:
            self.type = self.nodes[0].type
        else:
            self.type = None

    def symmetrical_merge(
        self,
        other_list: "NetworkNodeList",
    ):
        for other_node in other_list.nodes:
            self.__symmetrical_merge_helper(other_node)

    def asymmetrical_merge(
        self,
        other_list: "NetworkNodeList",
    ):
        for other_node in other_list.nodes:
            self.__asymmetrical_merge_helper(other_node)

    def internal_merge(
        self,
    ):
        if len(self.nodes) <= 1:
            if len(self.nodes) == 1:
                self.nodes[0].internal_merge()
            return
        skip_index = set()
        new_nodes = []
        for i, node in enumerate(self.nodes):
            node.internal_merge()
            if i in skip_index:
                continue
            if i == len(self.nodes) - 1:
                new_nodes.append(self.nodes[i])
                break
            x = i + 1
            new_nodes.append(node)
            for j, other_node in enumerate(self.nodes[x:]):
                if other_node in node or node in other_node:
                    node.symmetrical_merge(other_node)
                    skip_index.add(j + x)
        self.nodes = new_nodes

    def get_data(self) -> List[Dict]:
        rv = []
        for node in self.nodes:
            node_dict = node.as_dict()
            if node_dict:
                rv.append(node_dict)
        return rv

    def __add_node(self, node_data: Dict):
        new_node = NetworkNode(self, node_data, self.proc_node_list)
        self.nodes.append(new_node)

    def __symmetrical_merge_helper(self, other_node: "NetworkNode"):
        match = False
        cvt_other_node = other_node.converted
        for i, node in enumerate(self.nodes):
            if cvt_other_node in node:
                match = True
                node.symmetrical_merge(cvt_other_node)
                break
            elif node in cvt_other_node:
                node.symmetrical_merge(cvt_other_node)
                match = True
        if not match:
            self.nodes.append(cvt_other_node)

    def __asymmetrical_merge_helper(
        self,
        other_node: "NetworkNode",
    ):
        match = False
        cvt_other_node = other_node.converted
        for i, node in enumerate(self.nodes):
            if cvt_other_node in node:
                match = True
                node.asymmetrical_merge(cvt_other_node)
                break
        if not match:
            self.nodes.append(cvt_other_node)


def merge_proc_policies(
    mo: MergeObject,
    proc_data: List[Dict],
    other_proc_data: List[Dict],
    symmetric: bool,
):
    global BASE_NODE_LIST, MERGING_NODE_LIST
    if mo.disable_procs:
        BASE_NODE_LIST = ProcessNodeList([])
        MERGING_NODE_LIST = ProcessNodeList([])
        return []
    if BASE_NODE_LIST is None:
        BASE_NODE_LIST = ProcessNodeList(proc_data)
    MERGING_NODE_LIST = ProcessNodeList(other_proc_data)
    result = []
    if symmetric:
        BASE_NODE_LIST.symmetrical_merge(MERGING_NODE_LIST)
    else:
        BASE_NODE_LIST.asymmetrical_merge(MERGING_NODE_LIST)
    result = BASE_NODE_LIST.get_data()
    return result


def merge_ingress_or_egress(
    mo: MergeObject,
    base_data: List[Dict],
    other_data: List[Dict],
    symmetric: bool,
):
    if mo.disable_conns == lib.DISABLE_CONNS_ALL:
        return []
    disable_private = mo.disable_private_conns == lib.DISABLE_CONNS_ALL
    disable_public = mo.disable_public_conns == lib.DISABLE_CONNS_ALL
    disable_procs = mo.disable_procs == lib.DISABLE_PROCS_ALL
    net_node_list = NetworkNodeList(
        base_data,
        BASE_NODE_LIST,
        disable_private,
        disable_public,
        disable_procs,
    )
    other_node_list = NetworkNodeList(
        other_data,
        MERGING_NODE_LIST,
        disable_private,
        disable_public,
        disable_procs,
    )
    direction = net_node_list.type or other_node_list.type
    if not direction:
        return []
    if direction == lib.EGRESS_FIELD:
        if mo.disable_conns == lib.DISABLE_CONNS_EGRESS:
            return []
        if mo.disable_private_conns == lib.DISABLE_CONNS_EGRESS:
            net_node_list.ignore_private = True
            other_node_list.ignore_private = True
        if mo.disable_public_conns == lib.DISABLE_CONNS_EGRESS:
            net_node_list.ignore_public = True
            other_node_list.ignore_public = True
    else:
        if mo.disable_conns == lib.DISABLE_CONNS_INGRESS:
            return []
        if mo.disable_private_conns == lib.DISABLE_CONNS_INGRESS:
            net_node_list.ignore_private = True
            other_node_list.ignore_private = True
        if mo.disable_public_conns == lib.DISABLE_CONNS_INGRESS:
            net_node_list.ignore_public = True
            other_node_list.ignore_public = True
    net_node_list.internal_merge()
    other_node_list.internal_merge()
    if symmetric:
        net_node_list.symmetrical_merge(other_node_list)
    else:
        net_node_list.asymmetrical_merge(other_node_list)
    net_node_list.internal_merge()
    result = net_node_list.get_data()
    return result


def common_keys_merge(
    mo: MergeObject, base_data: Dict, other_data: Dict, symmetric: bool
):
    result = {}
    common_keys = set(base_data).intersection(set(other_data))
    for key, value in base_data.items():
        if key not in common_keys:
            continue
        if value == other_data.get(key):
            result[key] = value
    if len(result) > 0:
        return result
    return None


def wildcard_merge(
    mo: MergeObject, base_str: str, other_str: str, symmetric: bool
):
    "Result of the merge can be wildcarded"
    if symmetric:
        if base_str and other_str:
            if fnmatch.fnmatch(other_str, base_str):
                result = base_str
            elif fnmatch.fnmatch(base_str, other_str):
                result = other_str
            else:
                result = make_wildcard([base_str, other_str])
        else:
            result = None
    else:
        if base_str:
            if other_str and fnmatch.fnmatch(other_str, base_str):
                result = base_str
            else:
                result = None
        else:
            result = None
    return result


def all_eq_merge(mo: MergeObject, base_str: str, other_str: str, _):
    if base_str == other_str:
        result = base_str
    else:
        result = None
    return result


def keep_base_value_merge(mo: MergeObject, base_val: Any, other_val: Any, _):
    return base_val


def greatest_value_merge(
    mo: MergeObject, base_val, other_val, symmetric: bool
):
    if base_val is not None and other_val is None:
        result = base_val
    elif base_val is None and other_val is not None:
        result = other_val
    elif base_val is None and other_val is None:
        result = None
    elif base_val > other_val:
        result = base_val
    else:
        result = other_val
    return result


def string_list_merge(
    mo: MergeObject,
    base_value: Union[str, List[str]],
    other_value: Union[str, List[str]],
    _,
):
    if isinstance(base_value, str):
        base_value = [base_value]
    if isinstance(other_value, str):
        other_value = [other_value]
    string_set = set(base_value).union(set(other_value))
    return sorted(string_set)


def conditional_string_list_merge(
    mo: MergeObject,
    base_value: Union[str, List[str]],
    other_value: Union[str, List[str]],
    symmetric: bool,
):
    if isinstance(base_value, str) and isinstance(other_value, str):
        return wildcard_merge(mo, base_value, other_value, symmetric)
    else:
        return string_list_merge(mo, base_value, other_value, symmetric)


def unique_dict_list_merge(
    mo: MergeObject, base_value: List[Dict], other_value: List[dict], _
):
    rv = base_value.copy()
    for item in other_value:
        if item in base_value:
            continue
        rv.append(item)
    return rv


NET_POLICY_MERGE_SCHEMA = MergeSchema(
    NET_POLICY_FIELD,
    merge_functions={
        INGRESS_FIELD: merge_ingress_or_egress,
        EGRESS_FIELD: merge_ingress_or_egress,
    },
)
CONTAINER_SELECTOR_MERGE_SCHEMA = MergeSchema(
    CONT_SELECTOR_FIELD,
    merge_functions={
        IMAGE_FIELD: wildcard_merge,
        IMAGEID_FIELD: all_eq_merge,
        CONT_NAME_FIELD: wildcard_merge,
        CONT_ID_FIELD: all_eq_merge,
    },
    values_required=True,
    is_selector=True,
)
SVC_SELECTOR_MERGE_SCHEMA = MergeSchema(
    SVC_SELECTOR_FIELD,
    merge_functions={
        CGROUP_FIELD: all_eq_merge,
    },
    values_required=True,
    is_selector=True,
)
MACHINE_SELECTOR_MERGE_SCHEMA = MergeSchema(
    MACHINE_SELECTOR_FIELD,
    merge_functions={
        HOSTNAME_FIELD: conditional_string_list_merge,
        lib.MACHINE_UID_FIELD: conditional_string_list_merge,
    },
    values_required=True,
    is_selector=True,
)
POD_SELECTOR_MERGE_SCHEMA = MergeSchema(
    POD_SELECTOR_FIELD,
    merge_functions={
        MATCH_LABELS_FIELD: common_keys_merge,
    },
    values_required=True,
    is_selector=True,
)
NAMESPACE_SELECTOR_MERGE_SCHEMA = MergeSchema(
    NAMESPACE_SELECTOR_FIELD,
    merge_functions={
        MATCH_LABELS_FIELD: common_keys_merge,
    },
    values_required=True,
    is_selector=True,
)
TRACE_SELECTOR_MERGE_SCHEMA = MergeSchema(
    TRACE_SELECTOR_FIELD,
    merge_functions={
        lib.TRIGGER_ANCESTORS_FIELD: all_eq_merge,
        lib.TRIGGER_CLASS_FIELD: all_eq_merge,
    },
    values_required=True,
    is_selector=True,
)
USER_SELECTOR_MERGE_SCHEMA = MergeSchema(
    USER_SELECTOR_FIELD,
    merge_functions={
        lib.USERS_FIELD: string_list_merge,
        lib.INTERACTIVE_USERS_FIELD: string_list_merge,
        lib.NON_INTERACTIVE_USERS_FIELD: string_list_merge,
    },
)
PROCESS_SELECTOR_MERGE_SCHEMA = MergeSchema(
    USER_SELECTOR_FIELD,
    merge_functions={
        lib.NAME_FIELD: string_list_merge,
        lib.EXE_FIELD: string_list_merge,
        lib.EUSER_FIELD: string_list_merge,
        lib.INTERACTIVE_FIELD: keep_base_value_merge,
    },
)
SPEC_MERGE_SCHEMA = MergeSchema(
    SPEC_FIELD,
    sub_schemas={
        SVC_SELECTOR_FIELD: SVC_SELECTOR_MERGE_SCHEMA,
        CONT_SELECTOR_FIELD: CONTAINER_SELECTOR_MERGE_SCHEMA,
        MACHINE_SELECTOR_FIELD: MACHINE_SELECTOR_MERGE_SCHEMA,
        POD_SELECTOR_FIELD: POD_SELECTOR_MERGE_SCHEMA,
        NAMESPACE_SELECTOR_FIELD: NAMESPACE_SELECTOR_MERGE_SCHEMA,
        NET_POLICY_FIELD: NET_POLICY_MERGE_SCHEMA,
    },
    merge_functions={
        lib.ENABLED_FIELD: keep_base_value_merge,
        PROC_POLICY_FIELD: merge_proc_policies,
        RESPONSE_FIELD: keep_base_value_merge,
        lib.DISABLE_PROCS_FIELD: keep_base_value_merge,
        lib.DISABLE_CONNS_FIELD: keep_base_value_merge,
        lib.DISABLE_PU_CONNS_FIELD: keep_base_value_merge,
        lib.DISABLE_PR_CONNS_FIELD: keep_base_value_merge,
        lib.POL_MODE_FIELD: keep_base_value_merge,
    },
    values_required=True,
)
TRACE_SUPPRESSION_SPEC_MERGE_SCHEMA = MergeSchema(
    SPEC_FIELD,
    sub_schemas={
        SVC_SELECTOR_FIELD: SVC_SELECTOR_MERGE_SCHEMA,
        CONT_SELECTOR_FIELD: CONTAINER_SELECTOR_MERGE_SCHEMA,
        MACHINE_SELECTOR_FIELD: MACHINE_SELECTOR_MERGE_SCHEMA,
        POD_SELECTOR_FIELD: POD_SELECTOR_MERGE_SCHEMA,
        NAMESPACE_SELECTOR_FIELD: NAMESPACE_SELECTOR_MERGE_SCHEMA,
        TRACE_SELECTOR_FIELD: TRACE_SELECTOR_MERGE_SCHEMA,
        USER_SELECTOR_FIELD: USER_SELECTOR_MERGE_SCHEMA,
    },
    merge_functions={
        lib.ENABLED_FIELD: keep_base_value_merge,
        lib.ALLOWED_FLAGS_FIELD: unique_dict_list_merge,
        RESPONSE_FIELD: keep_base_value_merge,
    },
)


def make_wildcard(strs: List[str]):
    if len(strs) == 1:
        return strs[0]
    cmp_str = strs[0]
    if len(set(strs)) == 1:
        return cmp_str
    # Simple string match didn't work so lets see if there is a
    # better match (takes more computation)
    original_str = sub_str = strs[0]
    first_char = original_str[0]
    last_char = original_str[-1]
    for name in strs[1:]:
        if first_char != name[0]:
            first_char = None
        if last_char != name[-1]:
            last_char = None
        name = name.strip("*")
        match = SequenceMatcher(None, sub_str, name).find_longest_match(
            0, len(sub_str), 0, len(name)
        )
        match_si = match.a
        match_ei = match.a + match.size
        sub_str = sub_str[match_si:match_ei]
        if len(sub_str) < 3:
            break
    if len(sub_str) < 3:
        ret = None
    elif not (match.b == 0 and original_str.startswith(sub_str)) and not (
        match.b + match.size == len(name) and original_str.endswith(sub_str)
    ):
        ret = "*" + sub_str + "*"
    elif not (match.b == 0 and original_str.startswith(sub_str)):
        ret = "*" + sub_str
    elif not (
        match.b + match.size == len(name) and original_str.endswith(sub_str)
    ):
        ret = sub_str + "*"
    else:
        cli.err_exit(f"Bug detected in wildcard logic. Input:" f" '{strs}'.")
    return ret


def make_orig_line(line: str) -> str:
    return DEFAULT_WHITESPACE + line


def make_sub_line(line: str) -> str:
    return f"{lib.SUB_COLOR}{SUB_START}{line}{lib.COLOR_END}"


def make_add_line(line: str) -> str:
    return f"{lib.ADD_COLOR}{ADD_START}{line}{lib.COLOR_END}"


class DiffLines:
    def __init__(
        self,
        starting_index: float,
        ending_index: float,
        sub_lines: List[str],
        add_lines: List[str],
        deferred: bool = False,
    ) -> None:
        self.starting_index = starting_index
        self.ending_index = ending_index
        self.sub_lines = sub_lines
        self.add_lines = add_lines
        self.deferred = deferred

    def set_deferred(self, ending_index):
        self.starting_index = deferred_diff_si(ending_index)
        self.ending_index = deferred_diff_ei(ending_index)
        self.deferred = True

    def __repr__(self) -> str:
        first_line = next(iter(self.sub_lines), next(iter(self.add_lines), ""))
        rv = (
            f"DiffLines(si:{self.starting_index},"
            f' ei:{self.ending_index}, first_line:"{first_line})"'
        )
        return rv


class OriginalLines:
    def __init__(
        self,
        starting_index: float,
        ending_index: float,
        orig_lines: List[str],
        deferred: bool = False,
    ) -> None:
        self.starting_index = starting_index
        self.ending_index = ending_index
        self.orig_lines = orig_lines
        self.deferred = deferred

    def set_deferred(self, ending_index):
        self.starting_index = deferred_diff_si(ending_index)
        self.ending_index = deferred_diff_ei(ending_index)
        self.deferred = True

    def __repr__(self) -> str:
        rv = (
            f"OriginalLines(si:{self.starting_index},"
            f" ei:{self.ending_index}, first_line:"
            f'"{next(iter(self.orig_lines), "")}"'
        )
        return rv


def merge_diff_lines(dl1: DiffLines, dl2: DiffLines) -> DiffLines:
    rv = DiffLines(
        dl1.starting_index,
        dl2.ending_index,
        dl1.sub_lines + dl2.sub_lines,
        dl1.add_lines + dl2.add_lines,
        dl1.deferred,
    )
    return rv


def merge_original_lines(
    ol1: OriginalLines, ol2: OriginalLines
) -> OriginalLines:
    rv = OriginalLines(
        ol1.starting_index,
        ol2.ending_index,
        ol1.orig_lines + ol2.orig_lines,
        ol1.deferred,
    )
    return rv


def new_diff_si(ending_index) -> float:
    return ending_index - 0.45


def new_diff_ei(ending_index) -> float:
    return ending_index


def new_proc_si(ending_index) -> float:
    return ending_index - 0.15


def new_proc_ei(ending_index) -> float:
    return ending_index


def deferred_diff_si(ending_index) -> float:
    return ending_index - 0.25


def deferred_diff_ei(ending_index) -> float:
    return ending_index


def defer_diffs(
    diffs: List[Union[DiffLines, OriginalLines]], ending_index
) -> List[DiffLines]:
    for diff in diffs:
        diff.set_deferred(ending_index)


def un_defer_diffs(
    diffs: List[Union[DiffLines, OriginalLines]]
) -> List[DiffLines]:
    for diff in diffs:
        diff.deferred = False


def find_ancestor_indexes(
    yaml_lines, field, whitespace_length, starting_index, ending_index=None
) -> Optional[Tuple[int, int]]:
    if ending_index is None:
        ending_index = len(yaml_lines)
    pat = re.compile(rf"^ {{{whitespace_length}}}{field}:")
    pat2 = re.compile(
        rf"^ {{{max(whitespace_length - len(DEFAULT_WHITESPACE), 0)}}}"
        rf"{LIST_MARKER}{field}:"
    )
    end_pat = re.compile(rf"^ {{{whitespace_length}}}[^\s]+:")
    found_match = False
    for i, line in enumerate(yaml_lines[starting_index:ending_index]):
        if re.search(pat, line) or re.search(pat2, line):
            found_match = True
            starting_index = starting_index + i + 1
            if i + 1 != ending_index:
                si = starting_index + i + 1
                for x, next_line in enumerate(yaml_lines[si:ending_index]):
                    if re.search(end_pat, next_line):
                        ending_index = x + si
                        break
        if found_match:
            break
    if not found_match:
        return None
    whitespace_length += 2
    return starting_index, ending_index


def find_obj_indexes(
    yaml_lines: List[str],
    field: str,
    starting_index: int,
    ending_index: int,
    whitespace_length: int,
    obj_prefix: int = None,
) -> Optional[Tuple[int, int]]:
    pat = re.compile(rf"^ {{{whitespace_length}}}{field}:")
    pat2 = False
    if obj_prefix:
        pat2 = re.compile(rf"^{obj_prefix}{field}:")
    end_pat = re.compile(rf"^ {{{whitespace_length}}}[^\s]+:")
    found_match = False
    for i, line in enumerate(yaml_lines[starting_index:ending_index]):
        pat2_match = re.search(pat2, line) if pat2 else pat2
        if re.search(pat, line) or pat2_match:
            found_match = True
            starting_index = i + starting_index
            if i + 1 != ending_index:
                si = starting_index + 1
                for x, next_line in enumerate(yaml_lines[si:ending_index]):
                    if re.search(end_pat, next_line):
                        ending_index = x + si
                        break
        if found_match:
            break
    if not found_match:
        return None
    return starting_index, ending_index


def unify_diffs(
    diffs: List[Union[DiffLines, OriginalLines]]
) -> List[DiffLines]:
    sorted_diffs = sorted(diffs, key=lambda x: (x.deferred, x.starting_index))
    rv = []
    seen = set()
    for i, diff in enumerate(sorted_diffs):
        if i in seen:
            continue
        merged_diff = None
        x = i + 1
        if x == len(diffs):
            # The last diff is by itself
            rv.append(diff)
            break
        while x < len(sorted_diffs):
            next_diff = sorted_diffs[x]
            if (
                diff.ending_index == round(next_diff.starting_index)
                and isinstance(next_diff, type(diff))
                and diff.deferred == next_diff.deferred
            ):
                seen.add(x)
                # diffs are next to each other so merge
                if isinstance(diff, DiffLines):
                    if merged_diff is None:
                        merged_diff = merge_diff_lines(diff, next_diff)
                    else:
                        merged_diff = merge_diff_lines(merged_diff, next_diff)
                else:
                    if merged_diff is None:
                        merged_diff = merge_original_lines(diff, next_diff)
                    else:
                        merged_diff = merge_original_lines(
                            merged_diff, next_diff
                        )
                x += 1
            else:
                break
        if merged_diff:
            rv.append(merged_diff)
        else:
            rv.append(diff)
    return rv


def find_item_ending_index(
    item_si: int, list_ei: int, yaml_lines: List[str], item_prefix: str
):
    item_ei = list_ei
    if item_ei - item_si <= 0:
        raise Exception("Found bug, list ei must be greater than item si")
    elif item_ei - item_si > 1:
        si = item_si + 1
        for i, line in enumerate(yaml_lines[si:list_ei]):
            if line.startswith(item_prefix):
                item_ei = si + i
                break
    return item_ei


def find_list_item_prefix(ancestor_fields: List[str]) -> str:
    if len(ancestor_fields) == 0:
        return LIST_MARKER
    prefix = []
    found_actual_field = False
    for item in reversed(ancestor_fields):
        if item == LIST_MARKER and not found_actual_field:
            prefix.append(LIST_MARKER)
        else:
            found_actual_field = True
            prefix.append(DEFAULT_WHITESPACE)
    prefix.reverse()
    prefix.append(LIST_MARKER)
    if prefix[0] == DEFAULT_WHITESPACE:
        prefix.pop(0)
    prefix = "".join(prefix)
    return prefix


def diff_all_fields(
    original_data: Dict,
    other_data: Dict,
    yaml_lines: List[str],
    ancestor_fields: List[str] = [],
):
    starting_index = 0
    ending_index = len(yaml_lines)
    diffs = dict_diffs(
        original_data,
        other_data,
        yaml_lines,
        ancestor_fields,
        starting_index,
        ending_index,
    )
    new_lines = []
    for diff in diffs:
        if isinstance(diff, DiffLines):
            new_lines.extend(diff.sub_lines)
            new_lines.extend(diff.add_lines)
        else:
            new_lines.extend(diff.orig_lines)
        pass
    del yaml_lines[starting_index:ending_index]
    for i, new_line in enumerate(new_lines):
        yaml_lines.insert(i + starting_index, new_line)


def dict_diffs(
    original_data: Dict,
    other_data: Dict,
    yaml_lines: List[str],
    ancestor_fields: List[str],
    starting_index: int,
    ending_index: int,
    object_prefix: str = None,
) -> List[Union[DiffLines, OriginalLines]]:
    diffs = []
    fields = set(original_data).union(set(other_data))
    whitespace_length = len(ancestor_fields) * 2
    for field in fields:
        if field in original_data and field in other_data:
            if not isinstance(original_data[field], type(other_data[field])):
                cli.try_log(
                    f"Field type mismatch {field} | orig: "
                    f"'{type(original_data[field])}' "
                    f"new: '{type(other_data[field])}'"
                )
                continue
            indexes = find_obj_indexes(
                yaml_lines,
                field,
                starting_index,
                ending_index,
                whitespace_length,
                obj_prefix=object_prefix,
            )
            if indexes is None:
                raise Exception("Found bug! Unable to locate obj")
            obj_si, obj_ei = indexes
            if original_data[field] == other_data[field]:
                deferred = False
                if (
                    field == lib.CHILDREN_FIELD
                    and lib.PROC_POLICY_FIELD in ancestor_fields
                ):
                    deferred = True
                orig_lines = [
                    make_orig_line(o_line)
                    for o_line in yaml_lines[obj_si:obj_ei]
                ]
                diffs.append(
                    OriginalLines(
                        obj_si,
                        obj_ei,
                        orig_lines,
                        deferred=deferred,
                    )
                )
            elif isinstance(original_data[field], list):
                child_diffs = list_diffs(
                    original_data[field],
                    other_data[field],
                    yaml_lines,
                    obj_si,
                    obj_ei,
                    ancestor_fields + [field],
                )

                if field == lib.PROC_POLICY_FIELD:
                    un_defer_diffs(child_diffs)
                elif (
                    field == lib.CHILDREN_FIELD
                    and lib.PROC_POLICY_FIELD in ancestor_fields
                ):
                    defer_diffs(child_diffs, obj_ei)
                diffs.extend(child_diffs)
            elif isinstance(original_data[field], dict):
                diffs.append(
                    OriginalLines(
                        obj_si,
                        obj_si + 1,
                        [make_orig_line(yaml_lines[obj_si])],
                    )
                )
                diffs.extend(
                    dict_diffs(
                        original_data[field],
                        other_data[field],
                        yaml_lines,
                        ancestor_fields + [field],
                        obj_si,
                        obj_ei,
                    )
                )
            else:
                diff_yaml = yaml.dump(
                    {field: other_data[field]}, sort_keys=False
                )
                add_lines = [
                    " " * whitespace_length + new_line
                    for new_line in diff_yaml.splitlines()
                ]
                add_lines = [make_add_line(d_line) for d_line in add_lines]
                sub_lines = [
                    make_sub_line(o_line)
                    for o_line in yaml_lines[obj_si:obj_ei]
                ]
                diffs.append(DiffLines(obj_si, obj_ei, sub_lines, add_lines))
        if field in original_data and field not in other_data:
            indexes = find_obj_indexes(
                yaml_lines,
                field,
                starting_index,
                ending_index,
                whitespace_length,
                obj_prefix=object_prefix,
            )
            if indexes is None:
                raise Exception("Found bug! Unable to locate obj")
            deferred = False
            if (
                field == lib.CHILDREN_FIELD
                and lib.PROC_POLICY_FIELD in ancestor_fields
            ):
                deferred = True
            obj_si, obj_ei = indexes
            sub_lines = [
                make_sub_line(o_line) for o_line in yaml_lines[obj_si:obj_ei]
            ]
            diffs.append(
                DiffLines(obj_si, obj_ei, sub_lines, [], deferred=deferred)
            )
        if field not in original_data and field in other_data:
            deferred = False
            if (
                field == lib.CHILDREN_FIELD
                and lib.PROC_POLICY_FIELD in ancestor_fields
            ):
                deferred = True
            diff_yaml: str = yaml.dump(
                {field: other_data[field]}, sort_keys=False
            )
            add_lines = [
                DEFAULT_WHITESPACE * len(ancestor_fields) + new_line
                for new_line in diff_yaml.splitlines()
            ]
            add_lines = [make_add_line(d_line) for d_line in add_lines]
            diffs.append(
                DiffLines(
                    new_diff_si(ending_index),
                    new_diff_ei(ending_index),
                    [],
                    add_lines,
                    deferred=deferred,
                )
            )
    return unify_diffs(diffs)


def list_diffs(
    original_data: List,
    other_data: List,
    yaml_lines: List[str],
    starting_index: int,
    ending_index: int,
    ancestor_fields: List[str] = [],
):
    diffs = []
    parent_index = starting_index
    whitespace_length = (len(ancestor_fields) - 1) * 2
    indexes = find_ancestor_indexes(
        yaml_lines,
        ancestor_fields[-1],
        whitespace_length,
        starting_index,
        ending_index,
    )
    if indexes is None:
        raise Exception("Found bug! Unable to locate ancestor obj")
    else:
        starting_index, ending_index = indexes
    item_prefix = find_list_item_prefix(ancestor_fields)
    item_si = starting_index
    if ancestor_fields[-1] == lib.PROC_POLICY_FIELD or (
        ancestor_fields[-1] == lib.CHILDREN_FIELD
        and lib.PROC_POLICY_FIELD in ancestor_fields
    ):
        # We are diffing process nodes
        diffs.append(
            OriginalLines(
                parent_index,
                parent_index + 1,
                [make_orig_line(yaml_lines[parent_index])],
            )
        )
        seen = set()
        for proc_node in original_data:
            item_ei = find_item_ending_index(
                item_si, ending_index, yaml_lines, item_prefix
            )
            proc_id = proc_node["id"]
            seen.add(proc_id)
            id_match = False
            for other_node in other_data:
                if other_node["id"] == proc_id:
                    id_match = True
                    if proc_node == other_node:
                        orig_lines = [
                            make_orig_line(o_line)
                            for o_line in yaml_lines[item_si:item_ei]
                        ]
                        diffs.append(
                            OriginalLines(item_si, item_ei, orig_lines)
                        )
                    else:
                        diffs.extend(
                            dict_diffs(
                                proc_node,
                                other_node,
                                yaml_lines,
                                ancestor_fields,
                                item_si,
                                item_ei,
                                item_prefix,
                            )
                        )
                    break
            if not id_match:
                # proc node missing in new version
                sub_lines = [
                    make_sub_line(o_line)
                    for o_line in yaml_lines[item_si:item_ei]
                ]
                diffs.append(
                    DiffLines(
                        item_si,
                        item_ei,
                        sub_lines,
                        [],
                    )
                )
            item_si = item_ei
        for other_node in other_data:
            # See if there are any completely new processes
            proc_id = other_node["id"]
            if proc_id in seen:
                continue
            diff_yaml = yaml.dump([other_node], sort_keys=False)
            add_lines = [
                DEFAULT_WHITESPACE * (len(ancestor_fields) - 1) + new_line
                for new_line in diff_yaml.splitlines()
            ]
            add_lines = [make_add_line(d_line) for d_line in add_lines]
            diffs.append(
                DiffLines(
                    new_proc_si(ending_index),
                    new_proc_ei(ending_index),
                    [],
                    add_lines,
                    deferred=True,
                )
            )
    elif ancestor_fields[-1] in NET_POL_FIELDS:
        # We are dealing with a network policy
        length_diff = len(other_data) - len(original_data)
        diffs.append(
            OriginalLines(
                parent_index,
                parent_index + 1,
                [make_orig_line(yaml_lines[parent_index])],
            )
        )
        for orig_item, other_item in zip(original_data, other_data):
            item_ei = find_item_ending_index(
                item_si, ending_index, yaml_lines, item_prefix
            )
            if isinstance(orig_item, dict):
                diffs.extend(
                    dict_diffs(
                        orig_item,
                        other_item,
                        yaml_lines,
                        ancestor_fields,
                        starting_index=item_si,
                        ending_index=item_ei,
                        object_prefix=item_prefix,
                    )
                )
            else:
                raise Exception("list item type mismatch")
            item_si = item_ei
        if length_diff > 0:
            orig_data_len = len(original_data)
            diff_yaml = yaml.dump(other_data[orig_data_len:], sort_keys=False)
            add_lines = [
                DEFAULT_WHITESPACE * (len(ancestor_fields) - 1) + new_line
                for new_line in diff_yaml.splitlines()
            ]
            add_lines = [make_add_line(d_line) for d_line in add_lines]
            diffs.append(
                DiffLines(
                    new_diff_si(ending_index),
                    new_diff_ei(ending_index),
                    [],
                    add_lines,
                )
            )
        elif length_diff < 0:
            other_data_len = len(other_data)
            for orig_item in original_data[other_data_len:]:
                item_ei = find_item_ending_index(
                    item_si, ending_index, yaml_lines, item_prefix
                )
                sub_lines = [
                    make_sub_line(o_line)
                    for o_line in yaml_lines[item_si:item_ei]
                ]
                diffs.append(
                    DiffLines(
                        item_si,
                        item_ei,
                        sub_lines,
                        [],
                    )
                )
                item_si = item_ei
    elif ancestor_fields[-1] in OR_FIELDS:
        # Special case diffing the blocks under to and from in network
        diffs.append(
            OriginalLines(
                parent_index,
                parent_index + 1,
                [make_orig_line(yaml_lines[parent_index])],
            )
        )
        other_or_blocks = other_data.copy()
        for or_block in original_data:
            item_ei = find_item_ending_index(
                item_si, ending_index, yaml_lines, item_prefix
            )
            found_match = False
            for i, other_block in enumerate(other_or_blocks):
                if or_block == other_block:
                    found_match = True
                    orig_lines = [
                        make_orig_line(o_line)
                        for o_line in yaml_lines[item_si:item_ei]
                    ]
                    diffs.append(
                        OriginalLines(
                            item_si,
                            item_ei,
                            orig_lines,
                        )
                    )
                    break
            if found_match:
                other_or_blocks.pop(i)
            else:
                sub_lines = [
                    make_sub_line(o_line)
                    for o_line in yaml_lines[item_si:item_ei]
                ]
                diffs.append(
                    DiffLines(
                        item_si,
                        item_ei,
                        sub_lines,
                        [],
                    )
                )
            item_si = item_ei
        for other_block in other_or_blocks:
            diff_yaml = yaml.dump([other_block], sort_keys=False)
            add_lines = [
                DEFAULT_WHITESPACE * (len(ancestor_fields) - 1) + new_line
                for new_line in diff_yaml.splitlines()
            ]
            add_lines = [make_add_line(d_line) for d_line in add_lines]
            diffs.append(
                DiffLines(
                    new_diff_si(ending_index),
                    new_diff_ei(ending_index),
                    [],
                    add_lines,
                )
            )
    else:
        diffs.append(
            DiffLines(
                parent_index,
                parent_index + 1,
                [make_sub_line(yaml_lines[parent_index])],
                [make_add_line(yaml_lines[parent_index])],
            )
        )
        diff_yaml: str = yaml.dump(other_data, sort_keys=False)
        add_lines = [
            DEFAULT_WHITESPACE * (len(ancestor_fields) - 1) + new_line
            for new_line in diff_yaml.splitlines()
        ]
        add_lines = [make_add_line(d_line) for d_line in add_lines]
        sub_lines = [
            make_sub_line(o_line)
            for o_line in yaml_lines[starting_index:ending_index]
        ]
        diffs.append(
            DiffLines(
                starting_index,
                ending_index,
                sub_lines,
                add_lines,
            )
        )
    return unify_diffs(diffs)


def guardian_object_diff(original_data: Dict, other_data: Dict):
    """
    Calculate the difference between two guardian objects. This is an alternative
    output to string-based diffs focusing specifically on the process, and
    connection nodes within the guardian objects.

    Args:
        original_data (Dict): The original guardian object.
        other_data (Dict): The other guardian object to compare with.

    Returns:
        Dict: The difference between the two guardian objects.
    """
    rv = other_data.copy()
    rv[lib.SPEC_FIELD] = other_data[lib.SPEC_FIELD].copy()
    rv[lib.SPEC_FIELD][lib.PROC_POLICY_FIELD] = []
    rv[lib.SPEC_FIELD][lib.NET_POLICY_FIELD] = other_data[lib.SPEC_FIELD][
        lib.NET_POLICY_FIELD
    ].copy()
    rv[lib.SPEC_FIELD][lib.NET_POLICY_FIELD][INGRESS_FIELD] = []
    rv[lib.SPEC_FIELD][lib.NET_POLICY_FIELD][EGRESS_FIELD] = []
    orig_spec = original_data[lib.SPEC_FIELD]
    other_spec = other_data[lib.SPEC_FIELD]
    rv[lib.SPEC_FIELD][lib.PROC_POLICY_FIELD] = guardian_procs_diff(
        orig_spec, other_spec
    )
    rv[lib.SPEC_FIELD][lib.NET_POLICY_FIELD] = guardian_network_diff(
        orig_spec, other_spec
    )
    return rv


def guardian_procs_diff(original_spec, other_spec):
    def guardian_proc_diff(
        other_proc: Dict, orig_procs: List[Dict], rv: List[Dict]
    ):
        diff_proc = other_proc.copy()
        diff_proc.pop(lib.CHILDREN_FIELD, None)
        match_proc = None
        if not orig_procs:
            # If the process is new, document the node as added
            diff_proc["diff"] = "added"
        else:
            # Check to see if another process has a matching ID
            for orig_proc in orig_procs:
                if diff_proc[lib.ID_FIELD] == orig_proc[lib.ID_FIELD]:
                    cmp1 = diff_proc.copy()
                    cmp1.pop(lib.CHILDREN_FIELD, None)
                    cmp2 = orig_proc.copy()
                    cmp2.pop(lib.CHILDREN_FIELD, None)
                    # The processes are different, document the node as changed
                    if cmp1 != cmp2:
                        diff_proc["diff"] = "changed"
                    match_proc = orig_proc
                    break
            # We didn't find a matching ID so document the node as added
            if not match_proc:
                diff_proc["diff"] = "added"
        # Recursively check
        if lib.CHILDREN_FIELD in other_proc:
            diff_proc[lib.CHILDREN_FIELD] = []
            orig_children = (
                match_proc.get(lib.CHILDREN_FIELD, []) if match_proc else []
            )
            for c_proc in other_proc[lib.CHILDREN_FIELD]:
                guardian_proc_diff(
                    c_proc,
                    orig_children,
                    diff_proc[lib.CHILDREN_FIELD],
                )
        rv.append(diff_proc)

    def guardian_proc_check_removed(
        orig_proc: Dict, other_procs: List[Dict], rv: List[Dict]
    ):
        # Check to see if another process has a matching ID
        match_proc = None
        for other_proc in other_procs:
            if orig_proc[lib.ID_FIELD] == other_proc[lib.ID_FIELD]:
                match_proc = other_proc
                break
        if not match_proc:
            # If the process is removed, document the node and all of its children as removed
            diff_proc = deepcopy(orig_proc)
            guardian_proc_set_removed(diff_proc)
            rv.append(diff_proc)
        else:
            # Recursively check
            if lib.CHILDREN_FIELD in orig_proc:
                for c_proc in orig_proc[lib.CHILDREN_FIELD]:
                    guardian_proc_check_removed(
                        c_proc,
                        match_proc.get(lib.CHILDREN_FIELD, []),
                        orig_proc[lib.CHILDREN_FIELD],
                    )

    def guardian_proc_set_removed(diff_proc):
        diff_proc["diff"] = "removed"
        if lib.CHILDREN_FIELD in diff_proc:
            for c_proc in diff_proc[lib.CHILDREN_FIELD]:
                guardian_proc_set_removed(c_proc)

    rv = []
    orig_procs = original_spec[lib.PROC_POLICY_FIELD]
    other_procs = other_spec[lib.PROC_POLICY_FIELD]
    for other_proc in other_procs:
        guardian_proc_diff(other_proc, orig_procs, rv)
    for orig_proc in orig_procs:
        guardian_proc_check_removed(orig_proc, other_procs, rv)
    return rv


def guardian_network_diff(original_spec, other_spec):
    @dataclass(frozen=True)
    class GuardianNetNode:
        to_or_from: List
        ports: List[str]
        type: str
        processes: List[str] = None

        def as_dict(self):
            tf_str = (
                lib.FROM_FIELD
                if self.type == lib.INGRESS_FIELD
                else lib.TO_FIELD
            )
            rv = {
                tf_str: self.to_or_from,
                lib.PORTS_FIELD: self.ports,
            }
            if self.processes:
                rv[lib.PROCESSES_FIELD] = self.processes
            return rv

        def __hash__(self) -> int:
            return hash(json.dumps(self.as_dict(), sort_keys=True))

    def guardian_net_node_diff(
        other_nodes: Set[GuardianNetNode],
        orig_nodes: Set[GuardianNetNode],
        rv_nodes: List[Dict],
    ):
        added = other_nodes.difference(orig_nodes)
        for node in added:
            rv_node = node.as_dict()
            rv_node["diff"] = "added"
            rv_nodes.append(rv_node)
        removed = orig_nodes.difference(other_nodes)
        for node in removed:
            rv_node = node.as_dict()
            rv_node["diff"] = "removed"
            rv_nodes.append(rv_node)
        unchanged = other_nodes.intersection(orig_nodes)
        for node in unchanged:
            rv_node = node.as_dict()
            rv_nodes.append(rv_node)

    def make_individual_node_set(nodes: List[Dict]) -> Set[GuardianNetNode]:
        rv = set()
        for node in nodes:
            if lib.FROM_FIELD in node:
                type = lib.INGRESS_FIELD
            else:
                type = lib.EGRESS_FIELD
            to_or_from = node.get(lib.TO_FIELD, node.get(lib.FROM_FIELD, []))
            processes = node.get(lib.PROCESSES_FIELD, [])
            ports = node.get(lib.PORTS_FIELD, [])
            for tf in to_or_from:
                parse_to_from(rv, tf, processes, ports, type)
        return rv

    def parse_to_from(
        rv_set: Set,
        tf: Dict,
        processes: Optional[List[str]],
        ports: List[str],
        type: str,
    ):
        if lib.DNS_SELECTOR_FIELD in tf:
            for dns_name in tf[lib.DNS_SELECTOR_FIELD]:
                for port in ports:
                    if processes:
                        for proc in processes:
                            rv_set.add(
                                GuardianNetNode(
                                    [{lib.DNS_SELECTOR_FIELD: [dns_name]}],
                                    [port],
                                    type,
                                    [proc],
                                )
                            )
                    else:
                        rv_set.add(
                            GuardianNetNode(
                                {lib.DNS_SELECTOR_FIELD: [dns_name]},
                                [port],
                                type,
                            )
                        )
        else:
            for port in ports:
                if processes:
                    for proc in processes:
                        rv_set.add(GuardianNetNode([tf], [port], type, [proc]))
                else:
                    rv_set.add(GuardianNetNode([tf], [port], type))

    rv = {
        lib.INGRESS_FIELD: [],
        lib.EGRESS_FIELD: [],
    }
    orig_ingress = make_individual_node_set(
        original_spec[lib.NET_POLICY_FIELD][lib.INGRESS_FIELD]
    )
    other_ingress = make_individual_node_set(
        other_spec[lib.NET_POLICY_FIELD][lib.INGRESS_FIELD]
    )
    guardian_net_node_diff(other_ingress, orig_ingress, rv[lib.INGRESS_FIELD])
    orig_egress = make_individual_node_set(
        original_spec[lib.NET_POLICY_FIELD][lib.EGRESS_FIELD]
    )
    other_egress = make_individual_node_set(
        other_spec[lib.NET_POLICY_FIELD][lib.EGRESS_FIELD]
    )
    guardian_net_node_diff(other_egress, orig_egress, rv[lib.EGRESS_FIELD])
    return rv
