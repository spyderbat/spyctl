import ipaddress as ipaddr
from os import path
from typing import Dict, Generator, List, Optional, TypeVar, Union, Tuple
from difflib import SequenceMatcher

import yaml
from typing_extensions import Self

import spyctl.spyctl_lib as lib
import spyctl.cli as cli
import spyctl.resources.baselines as spyctl_baselines

SPECIAL_FUNCTIONS = {}


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


# def merge_objects(
#     objects: List[Dict], fields=[lib.METADATA_FIELD, lib.SPEC_FIELD]
# ) -> Dict:
#     rv = {}

#     for field in fields:
#         merge_subfield(objects, field, rv)


# def merge_with_objects(
#     base: Dict,
#     objects: List[Dict],
#     fields=[lib.METADATA_FIELD, lib.SPEC_FIELD],
# ) -> Tuple[Dict, Dict]:
#     merged_fields = merge_objects(objects, fields)
#     deviations = find_deviations(base, merged_fields, fields)
#     merged_fields = merge_objects([merged_fields, base], fields)
#     for field in merged_fields:
#         base[field] = merged_fields[field]
#     return deviations


# class MergeObject:
#     def __init__(self) -> None:
#         pass


# class ProcessNode:
#     def __init__(self, node: Dict, node_list: "ProcessNodeList") -> None:
#         self.node = node.copy()
#         self.id = node["id"]
#         self.children = []
#         self.appearances = set((current_fingerprint,))
#         if "children" in self.node:
#             self.children = [
#                 ProcessNode(child) for child in self.node["children"]
#             ]
#         ProcessID.all_ids.append(self.id)

#     def __eq__(self, other):
#         if isinstance(other, self.__class__):
#             if self.node.get("name") != other.node.get("name"):
#                 return False
#             if self.node.get("euser") != other.node.get("euser"):
#                 return False
#             # exe field is a list - does that need handling?
#             self_exe = path.split(self.node["exe"][0])
#             other_exe = path.split(other.node["exe"][0])
#             if self_exe[0] == other_exe[0] and self_exe[1] != other_exe[1]:
#                 self_start = self_exe[1][:3]
#                 other_start = other_exe[1][:3]
#                 merged = make_wildcard(
#                     (self.node["exe"][0], other.node["exe"][0])
#                 )
#                 if self_start == other_start:
#                     new_exe = input(
#                         f"Merge {self.node['exe'][0]} and"
#                         f" {other.node['exe'][0]} to {merged}?"
#                         " (y/n/custom merge): "
#                     )
#                     if new_exe.lower() == "y":
#                         new_exe = merged
#                     if new_exe.lower() != "n":
#                         self.node["exe"][0] = new_exe
#                         other.node["exe"][0] = new_exe
#             return self.node.get("exe") == other.node.get("exe")
#         else:
#             return False

#     def extend(self, other: Self):
#         if other != self:
#             raise ValueError("Other process did not match")
#         self.id.extend(other.id)
#         self.appearances.update(other.appearances)
#         for child in other.children:
#             match = find(self.children, child)
#             if match is not None:
#                 match.extend(child)
#             else:
#                 self.children.append(child)

#     def update_node(self):
#         self.node["id"] = self.id.unique_id
#         if len(self.children) == 0:
#             if "children" in self.node:
#                 del self.node["children"]
#             return
#         self.node["children"] = self.children
#         for child in self.children:
#             child.update_node()


# def merge_subfield(objs, key, ret):
#     sub_list = None
#     try:
#         sub_list = [obj[key].copy() for obj in objs]
#     except AttributeError:
#         try:
#             sub_list = [obj[key] for obj in objs]
#         except KeyError:
#             return
#     except KeyError:
#         return
#     except Exception:
#         print("hi")
#     new = None
#     if key in spec_fns:
#         new = spec_fns[key](sub_list)
#     else:
#         new = globals()[f"merge_{key}"](sub_list)
#     if new is not None:
#         ret[key] = new


# def wildcard_merge(key):
#     global SPECIAL_FUNCTIONS

#     def do_wildcard(strs: List[str]):
#         ret = WildcardList()
#         for string in iter_prints(strs):
#             ret.add_str(string)
#         return ret

#     SPECIAL_FUNCTIONS[key] = do_wildcard


# def if_all_eq_merge(key):
#     def do_if_all_eq(objs: list):
#         ret = IfAllEqList()
#         for obj in iter_prints(objs):
#             ret.add_obj(obj)
#         return ret

#     spec_fns[key] = do_if_all_eq
