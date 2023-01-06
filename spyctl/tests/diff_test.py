import difflib
from typing import Dict, List, Optional, Tuple, NamedTuple, Union
from collections import namedtuple

import yaml
import re

DIFF_START = "<<<<<<< HEAD"
DIFF_CENTER = "======="
DIFF_END = ">>>>>>> DIFF END"
ADD_START = "+ "
SUB_START = "- "
ADD_COLOR = "\033[38;5;35m"
SUB_COLOR = "\033[38;5;203m"
COLOR_END = "\033[0m"
LIST_MARKER = "- "
DEFAULT_WHITESPACE = "  "

# x = {
#     "name": "sh",
#     "exe": ["/bin/dash"],
#     "id": "sh_0",
#     "euser": "root",
#     "children": [{"name": "foo", "exe": "/bin/foo"}],
# }
# x2 = {
#     "name": "bash",
#     "exe": ["/bin/dash", "/sbin/dash"],
#     "id": "sh_0",
#     "euser": "root",
#     # "tag": "foobar",
#     "children": [{"name": "bar", "exe": "/bin/bar"}],
# }
# y = {
#     "name": "bat1292393",
#     "exe": ["/bin/grimreaper"],
#     "id": "bat_0",
#     "euser": ["admin"],
# }
# y2 = {
#     # "tag": "foobar",
#     "name": "bat*",
#     "exe": ["/bin/grimreaper"],
#     "id": "bat_0",
#     "euser": ["admin"],
#     "children": [{"name": "foo", "exe": "/sbin/foo"}],
# }


# class ObjIndexes:
#     def __init__(
#         self,
#         ancestor_indexes: Union[Tuple, "ObjIndexes"],
#         yaml_lines: List[str],
#         field: str,
#         is_list=False,
#     ) -> None:
#         self.obj_si = None
#         self.obj_ei = None
#         self.merged_obj_si = None
#         self.merged_obj_ei = None
#         if isinstance(ancestor_indexes, ObjIndexes):
#             self.parent_si,
#             self.parent_ei =
#             self.merged_parent_si,
#             self.merged_parent_ei,
#         else:
#             (
#                 self.parent_si,
#                 self.parent_ei,
#                 self.merged_parent_si,
#                 self.merged_parent_ei,
#             ) = ancestor_indexes
#         obj_indexes = find_obj_indexes(
#             yaml_lines,
#         )
#         if obj_indexes:


base = {
    "apiVersion": "spyderbat/v1",
    "kind": "SpyderbatBaseline",
    "metadata": {
        "name": "guyduchatelet/spyderbat-demo:1",
        "type": "container",
        "latestTimestamp": 1672339696.3252509,
    },
    "spec": {
        "containerSelector": {
            "image": "guyduchatelet/spyderbat-demo:1",
            "imageID": "sha256:6e2e1bce440ec41f53e849e56d5c6716ed7f1e1fa614d8dca2bbda49e5cde29e",
        },
        "processPolicy": [
            {
                "name": "python",
                "exe": ["/usr/local/bin/python3.7"],
                "id": "python_0",
                "euser": ["root"],
                "children": [
                    {
                        "name": "python",
                        "exe": ["/usr/local/bin/python3.7"],
                        "id": "python_1",
                    },
                    {
                        "name": "sh",
                        "exe": ["/usr/bin/dash"],
                        "id": "sh_0",
                    },
                ],
            }
        ],
        "networkPolicy": {
            "ingress": [
                {
                    "from": [{"ipBlock": {"cidr": "192.168.38.252/32"}}],
                    "processes": ["python_2"],
                    "ports": [{"protocol": "TCP", "port": 5000}],
                }
            ],
            "egress": [
                {
                    "to": [
                        {
                            "dnsSelector": [
                                "mongodb.rsvp-svc-dev.svc.cluster.local",
                            ]
                        },
                        {
                            "ipBlock": {
                                "cidr": "192.168.38.0/24",
                                "except": [{"cidr": "192.168.38.10/32"}],
                            },
                        },
                    ]
                }
            ],
        },
    },
}
merged = {
    "apiVersion": "spyderbat/v1",
    "kind": "SpyderbatBaseline",
    "metadata": {
        "name": "guyduchatelet/spyderbat-demo:1",
        "type": "container",
        "latestTimestamp": 1672339696.3252509,
    },
    "spec": {
        "containerSelector": {
            "image": "guyduchatelet/spyderbat-demo:1",
            "imageID": "sha256:6e2e1bce440ec41f53e849e56d5c6716ed7f1e1fa614d8dca2bbda49e5cde29e",
        },
        "processPolicy": [
            {
                "name": "pyth*",
                "exe": ["/usr/local/bin/python*"],
                "id": "python_0",
                "euser": ["root"],
                "children": [
                    {
                        "name": "pyth*",
                        "exe": ["/usr/local/bin/python3.7"],
                        "id": "python_1",
                    },
                    {
                        "name": "sh",
                        "exe": ["/usr/bin/dash"],
                        "id": "sh_0",
                    },
                ],
            }
        ],
        "networkPolicy": {
            "ingress": [
                {
                    "from": [{"ipBlock": {"cidr": "192.168.38.253/32"}}],
                    "processes": ["python_2"],
                    "ports": [{"protocol": "TCP", "port": 5000}],
                }
            ],
            "egress": [
                {
                    "to": [
                        {
                            "dnsSelector": [
                                "mongodb.rsvp-svc-dev.svc.cluster.loca",
                                "google.com",
                            ]
                        },
                        {
                            "ipBlock": {
                                "cidr": "192.168.38.0/24",
                                "except": [{"cidr": "192.168.38.11/32"}],
                            },
                        },
                    ]
                }
            ],
        },
    },
}


def make_orig_line(line: str) -> str:
    return DEFAULT_WHITESPACE + line


def make_sub_line(line: str) -> str:
    return f"{SUB_COLOR}{SUB_START}{line}{COLOR_END}"


def make_add_line(line: str) -> str:
    return f"{ADD_COLOR}{ADD_START}{line}{COLOR_END}"


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


def deferred_diff_si(ending_index) -> float:
    return ending_index - 0.25


def deferred_diff_ei(ending_index) -> float:
    return ending_index


def defer_diffs(
    diffs: List[Union[DiffLines, OriginalLines]], ending_index
) -> List[DiffLines]:
    for diff in diffs:
        diff.set_deferred(ending_index)


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

    # if indexes is None:
    #     print("Found bug! Unable to locate ancestor obj")
    #     return
    # else:
    #     starting_index, ending_index = indexes
    # fields = set(original_data).union(other_data)
    # whitespace_length = len(ancestor_fields) * 2
    # diffs = []
    # for field in fields:
    #     if field in original_data and field in other_data:
    #         if isinstance(original_data[field], str):
    #             if original_data[field] == other_data[field]:
    #                 continue
    #         elif isinstance(original_data[field], list):
    #             if isinstance(
    #                 next(iter(original_data[field]), None), dict
    #             ) or sorted(original_data[field]) == sorted(other_data[field]):
    #                 continue
    #         elif isinstance(original_data[field], dict):
    #             continue
    #         indexes = find_obj_indexes(
    #             yaml_lines,
    #             field,
    #             starting_index,
    #             ending_index,
    #             whitespace_length,
    #         )
    #         if indexes is None:
    #             print("Found bug! Unable to locate obj")
    #             return
    #         obj_si, obj_ei = indexes
    #         diff_yaml = yaml.dump({field: other_data[field]}, sort_keys=False)
    #         add_lines = [
    #             f" " * whitespace_length + new_line
    #             for new_line in diff_yaml.splitlines()
    #         ]
    #         diffs.append(
    #             field_diff(
    #                 obj_si, obj_ei, yaml_lines[obj_si:obj_ei], add_lines
    #             )
    #         )
    #     if field in original_data and field not in other_data:
    #         # if isinstance(original_data[field], dict):
    #         #     continue
    #         indexes = find_obj_indexes(
    #             yaml_lines,
    #             field,
    #             starting_index,
    #             ending_index,
    #             whitespace_length,
    #         )
    #         if indexes is None:
    #             print("Found bug! Unable to locate obj")
    #             return
    #         obj_si, obj_ei = indexes
    #         diffs.append(
    #             field_diff(obj_si, obj_ei, yaml_lines[obj_si:obj_ei], [])
    #         )
    #     if field not in original_data and field in other_data:
    #         # if isinstance(other_data[field], dict) or (
    #         #     isinstance(other_data[field], list)
    #         #     and isinstance(next(iter(other_data[field]), None), dict)
    #         # ):
    #         #     diff_yaml: str = field
    #         # else:
    #         diff_yaml: str = yaml.dump(
    #             {field: other_data[field]}, sort_keys=False
    #         )
    #         add_lines = [
    #             f" " * whitespace_length + new_line
    #             for new_line in diff_yaml.splitlines()
    #         ]
    #         diffs.append(
    #             field_diff(ending_index, ending_index, [], add_lines)
    #         )
    # diffs = unify_diffs(diffs)
    # if len(diffs) == 0:
    #     return
    # new_lines = []
    # diff_index = 0
    # seen = set()
    # for i in range(starting_index, ending_index):
    #     if i in seen:
    #         continue
    #     if diff_index < len(diffs):
    #         diff = diffs[diff_index]
    #         if diff.starting_index == i:
    #             new_lines.append(
    #                 "\033[32m"
    #                 + f"<" * whitespace_length
    #                 + DIFF_START
    #                 + "\033[0m"
    #             )
    #             new_lines.extend(diff.orig_lines)
    #             new_lines.append(
    #                 "\033[32m"
    #                 + f"=" * whitespace_length
    #                 + DIFF_CENTER
    #                 + "\033[0m"
    #             )
    #             new_lines.extend(diff.add_lines)
    #             new_lines.append(
    #                 "\033[34m"
    #                 + f">" * whitespace_length
    #                 + DIFF_END
    #                 + "\033[0m"
    #             )
    #             for x in range(i, diff.ending_index):
    #                 seen.add(x)
    #             diff_index += 1
    #             continue
    #     new_lines.append(yaml_lines[i])
    # if diff_index < len(diffs):
    #     for i in range(diff_index, len(diffs)):
    #         new_lines.append(
    #             "\033[32m" + f"<" * whitespace_length + DIFF_START + "\033[0m"
    #         )
    #         new_lines.extend(diff.orig_lines)
    #         new_lines.append(
    #             "\033[32m" + f"=" * whitespace_length + DIFF_CENTER + "\033[0m"
    #         )
    #         new_lines.extend(diff.add_lines)
    #         new_lines.append(
    #             "\033[34m" + f">" * whitespace_length + DIFF_END + "\033[0m"
    #         )
    #         for x in range(i, diff.ending_index):
    #             seen.add(x)
    #         diff_index += 1
    #         continue
    # del yaml_lines[starting_index:ending_index]
    # for i, new_line in enumerate(new_lines):
    #     yaml_lines.insert(i + starting_index, new_line)


net_node_fields = {"ipBlock"}


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
    # if len(ancestor_fields) > 0 and starting_index == 0:
    #     whitespace_length = (len(ancestor_fields) - 1) * 2
    #     indexes = find_ancestor_indexes(
    #         yaml_lines, ancestor_fields[-1], whitespace_length, starting_index
    #     )
    #     if indexes is None:
    #         raise Exception("Found bug! Unable to locate ancestor obj")
    #     else:
    #         starting_index, ending_index = indexes
    fields = set(original_data).union(set(other_data))
    whitespace_length = len(ancestor_fields) * 2
    for field in fields:
        if field in original_data and field in other_data:
            if not isinstance(original_data[field], type(other_data[field])):
                print("Field type mismatch")
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
                if isinstance(original_data[field], list):
                    if len(original_data[field]) > 0 and isinstance(
                        original_data[field], dict
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
                if isinstance(
                    next(iter(original_data[field]), None), dict
                ) or isinstance(next(iter(other_data[field]), None), dict):
                    defer_diffs(child_diffs, obj_ei)
                    diffs.extend(child_diffs)
                else:
                    diffs.extend(child_diffs)
            elif isinstance(original_data[field], dict):
                if starting_index > 0:
                    if field in net_node_fields:
                        diffs.append(
                            DiffLines(
                                starting_index,
                                starting_index + 1,
                                [make_sub_line(yaml_lines[starting_index])],
                                [make_add_line(yaml_lines[starting_index])],
                            )
                        )
                    else:
                        diffs.append(
                            OriginalLines(
                                starting_index,
                                starting_index + 1,
                                [make_orig_line(yaml_lines[starting_index])],
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
                    f" " * whitespace_length + new_line
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
                isinstance(original_data[field], list)
                and len(original_data[field]) > 0
                and isinstance(original_data[field][0], dict)
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
                isinstance(other_data[field], list)
                and len(other_data[field]) > 0
                and isinstance(other_data[field][0], dict)
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
    length_diff = len(other_data) - len(original_data)
    item_prefix = find_list_item_prefix(ancestor_fields)
    item_si = starting_index
    if isinstance(next(iter(original_data), None), Dict) and isinstance(
        next(iter(other_data), None), Dict
    ):
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


yaml_orig: str = yaml.dump(base, sort_keys=False)
yaml_merged: str = yaml.dump(merged, sort_keys=False)
print("Original\n")
print(yaml_orig)
print("Merged\n")
print(yaml_merged)
yaml_lines = yaml_orig.splitlines()
diff_all_fields(
    base,
    merged,
    yaml_lines,
    [],
)
print("Diff\n")
print("\n".join(yaml_lines))
