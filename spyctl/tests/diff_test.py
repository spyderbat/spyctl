import difflib
from typing import Dict, List, Optional, Tuple
from collections import namedtuple

import yaml
import re

DIFF_START = "<<<<<<< HEAD"
DIFF_CENTER = "======="
DIFF_END = ">>>>>>> DIFF END"

x = {
    "name": "sh",
    "exe": ["/bin/dash"],
    "id": "sh_0",
    "euser": "root",
    "children": [{"name": "foo", "exe": "/bin/foo"}],
}
x2 = {
    "name": "bash",
    "exe": ["/bin/dash", "/sbin/dash"],
    "id": "sh_0",
    "euser": "root",
    # "tag": "foobar",
    "children": [{"name": "bar", "exe": "/bin/bar"}],
}
y = {
    "name": "bat1292393",
    "exe": ["/bin/grimreaper"],
    "id": "bat_0",
    "euser": ["admin"],
}
y2 = {
    # "tag": "foobar",
    "name": "bat*",
    "exe": ["/bin/grimreaper"],
    "id": "bat_0",
    "euser": ["admin"],
    "children": [{"name": "foo", "exe": "/sbin/foo"}],
}
proc1 = {"spec": {"proc1": y, "proc2": x}}
proc2 = {"spec": {"proc1": y2, "proc2": x2}}


def find_ancestor_indexes(
    yaml_lines, ancestor_fields=[]
) -> Optional[Tuple[int, int]]:
    starting_index = 0
    ending_index = len(yaml_lines)
    whitespace_length = 0
    for field in ancestor_fields:
        if whitespace_length == 0:
            pat = re.compile(f"^{field}:")
            end_pat = re.compile(f"^(?! +)(?!- ).+:")
        else:
            pat = re.compile(f"^ {{{whitespace_length}}}{field}:")
            end_pat = re.compile(f"^ {{{whitespace_length}}}(?! +)(?!- ).+:")
        found_match = False
        for i, line in enumerate(yaml_lines[starting_index:ending_index]):
            if re.search(pat, line):
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
) -> Optional[Tuple[int, int]]:
    pat = re.compile(rf" {{{whitespace_length}}}{field}:")
    end_pat = re.compile(rf" {{{whitespace_length}}}(?!- ).+:")
    found_match = False
    for i, line in enumerate(yaml_lines[starting_index:ending_index]):
        if re.search(pat, line):
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


field_diff = namedtuple(
    "field_diff",
    ["starting_index", "ending_index", "orig_lines", "diff_lines"],
)


def unify_diffs(diffs: List[field_diff]) -> List[field_diff]:
    diffs.sort(key=lambda x: x.starting_index)
    rv = []
    seen = set()
    for i, diff in enumerate(diffs):
        if i in seen:
            continue
        merged_diff = None
        x = i + 1
        if x == len(diff):
            # The last diff is by itself
            rv.append(diff)
        while x < len(diffs):
            next_diff = diffs[x]
            if diff.ending_index == next_diff.starting_index:
                seen.add(x)
                # diffs are next to each other so merge
                if merged_diff is None:
                    merged_diff = field_diff(
                        diff.starting_index,
                        next_diff.ending_index,
                        diff.orig_lines + next_diff.orig_lines,
                        diff.diff_lines + next_diff.diff_lines,
                    )
                else:
                    merged_diff = field_diff(
                        merged_diff.starting_index,
                        next_diff.ending_index,
                        merged_diff.orig_lines + next_diff.orig_lines,
                        merged_diff.diff_lines + next_diff.diff_lines,
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
    _,
    ancestor_fields: List[str] = [],
):
    indexes = find_ancestor_indexes(yaml_lines, ancestor_fields)
    if indexes is None:
        print("Found bug! Unable to locate ancestor obj")
        return
    else:
        starting_index, ending_index = indexes
    fields = set(original_data).union(other_data)
    whitespace_length = len(ancestor_fields) * 2
    diffs = []
    for field in fields:
        if field in original_data and field in other_data:
            if isinstance(original_data[field], str):
                if original_data[field] == other_data[field]:
                    continue
            elif isinstance(original_data[field], list):
                if isinstance(
                    next(iter(original_data[field]), None), dict
                ) or sorted(original_data[field]) == sorted(other_data[field]):
                    continue
            elif isinstance(original_data[field], dict):
                continue
            indexes = find_obj_indexes(
                yaml_lines,
                field,
                starting_index,
                ending_index,
                whitespace_length,
            )
            if indexes is None:
                print("Found bug! Unable to locate obj")
                return
            obj_si, obj_ei = indexes
            diff_yaml = yaml.dump({field: other_data[field]}, sort_keys=False)
            diff_lines = [
                f" " * whitespace_length + new_line
                for new_line in diff_yaml.splitlines()
            ]
            diffs.append(
                field_diff(
                    obj_si, obj_ei, yaml_lines[obj_si:obj_ei], diff_lines
                )
            )
        if field in original_data and field not in other_data:
            # if isinstance(original_data[field], dict):
            #     continue
            indexes = find_obj_indexes(
                yaml_lines,
                field,
                starting_index,
                ending_index,
                whitespace_length,
            )
            if indexes is None:
                print("Found bug! Unable to locate obj")
                return
            obj_si, obj_ei = indexes
            diffs.append(
                field_diff(obj_si, obj_ei, yaml_lines[obj_si:obj_ei], [])
            )
        if field not in original_data and field in other_data:
            # if isinstance(other_data[field], dict) or (
            #     isinstance(other_data[field], list)
            #     and isinstance(next(iter(other_data[field]), None), dict)
            # ):
            #     diff_yaml: str = field
            # else:
            diff_yaml: str = yaml.dump(
                {field: other_data[field]}, sort_keys=False
            )
            diff_lines = [
                f" " * whitespace_length + new_line
                for new_line in diff_yaml.splitlines()
            ]
            diffs.append(
                field_diff(ending_index, ending_index, [], diff_lines)
            )
    diffs = unify_diffs(diffs)
    if len(diffs) == 0:
        return
    new_lines = []
    diff_index = 0
    seen = set()
    for i in range(starting_index, ending_index):
        if i in seen:
            continue
        if diff_index < len(diffs):
            diff = diffs[diff_index]
            if diff.starting_index == i:
                new_lines.append(
                    "\033[32m"
                    + f"<" * whitespace_length
                    + DIFF_START
                    + "\033[0m"
                )
                new_lines.extend(diff.orig_lines)
                new_lines.append(
                    "\033[32m"
                    + f"=" * whitespace_length
                    + DIFF_CENTER
                    + "\033[0m"
                )
                new_lines.extend(diff.diff_lines)
                new_lines.append(
                    "\033[34m"
                    + f">" * whitespace_length
                    + DIFF_END
                    + "\033[0m"
                )
                for x in range(i, diff.ending_index):
                    seen.add(x)
                diff_index += 1
                continue
        new_lines.append(yaml_lines[i])
    if diff_index < len(diffs):
        for i in range(diff_index, len(diffs)):
            new_lines.append(
                "\033[32m" + f"<" * whitespace_length + DIFF_START + "\033[0m"
            )
            new_lines.extend(diff.orig_lines)
            new_lines.append(
                "\033[32m" + f"=" * whitespace_length + DIFF_CENTER + "\033[0m"
            )
            new_lines.extend(diff.diff_lines)
            new_lines.append(
                "\033[34m" + f">" * whitespace_length + DIFF_END + "\033[0m"
            )
            for x in range(i, diff.ending_index):
                seen.add(x)
            diff_index += 1
            continue
    del yaml_lines[starting_index:ending_index]
    for i, new_line in enumerate(new_lines):
        yaml_lines.insert(i + starting_index, new_line)


yaml_orig: str = yaml.dump(proc1, sort_keys=False)
yaml_merged: str = yaml.dump(proc2, sort_keys=False)
print("Original\n")
print(yaml_orig)
print("Merged\n")
print(yaml_merged)
yaml_lines = yaml_orig.splitlines()
diff_all_fields(
    proc1["spec"]["proc1"],
    proc2["spec"]["proc1"],
    yaml_lines,
    None,
    ["spec", "proc1"],
)
diff_all_fields(
    proc1["spec"]["proc2"],
    proc2["spec"]["proc2"],
    yaml_lines,
    None,
    ["spec", "proc2"],
)
print("Diff\n")
print("\n".join(yaml_lines))
