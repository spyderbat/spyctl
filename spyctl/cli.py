import json
import os
import re
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from pydoc import pager, pipepager
from typing import Callable, Dict, List

import yaml

import spyctl.spyctl_lib as lib

yaml.Dumper.ignore_aliases = lambda *args: True

WARNING_MSG = "is_warning"
WARNING_COLOR = lib.WARNING_COLOR
COLOR_END = lib.COLOR_END


def try_log(*args, **kwargs):
    lib.try_log(*args, **kwargs)


def try_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
        sys.stdout.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(1)


def unsupported_output_msg(output: str) -> str:
    return f"'--output {output}' is not supported for this command."


YES_OPTION = False


def set_yes_option():
    global YES_OPTION
    YES_OPTION = True


def query_yes_no(question, default="yes", ignore_yes_option=False):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
            It must be "yes" (the default), "no" or None (meaning
            an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        if YES_OPTION and not ignore_yes_option:
            return True
        sys.stderr.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stderr.write(
                "Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n"
            )


def notice(notice_msg):
    """Notify the user of something, wait for input

    "notice_msg" is a string that is presented to the user.
    """
    if YES_OPTION:
        return
    prompt = " [ok] "
    sys.stderr.write(notice_msg + prompt)
    input()


def show(
    obj,
    output,
    alternative_outputs: Dict[str, Callable] = {},
    dest=lib.OUTPUT_DEST_STDOUT,
    output_fn=None,
    ndjson=False,
):
    """Display or save python object

    Args:
        obj (any): python object to be displayed or saved
        output (str): the format of the output
        alternative_outputs (Dict[str, Callable], optional): A
            dictionary of formats to callables for custom outputs.
            Defaults to {}. Callable must return a string.
        dest (str, optional): Destination of the output. Defaults to
            lib.OUTPUT_DEST_STDOUT.
        output_fn (str, optional): Filename if outputting to a file.
            Defaults to None.
        ndjson (bool, optional): If output is json, output the json on a
            single line. Defaults to False
    """
    out_data = None
    if output == lib.OUTPUT_YAML:
        out_data = yaml.dump(obj, sort_keys=False)
        if output_fn:
            output_fn += ".yaml"
    elif output == lib.OUTPUT_JSON:
        if ndjson:
            if _seq_but_not_str(obj):
                out_data = []
                for item in obj:
                    out_data.append(json.dumps(item))
                out_data = "\n".join(out_data)
            else:
                out_data = json.dumps(obj)
        else:
            out_data = json.dumps(obj, sort_keys=False, indent=2)
        if output_fn:
            output_fn += ".json"
    elif output == lib.OUTPUT_RAW:
        out_data = obj
    elif output in alternative_outputs:
        out_data = alternative_outputs[output](obj)
    else:
        try_log(unsupported_output_msg(output), is_warning=True)
    if out_data:
        if dest == lib.OUTPUT_DEST_FILE:
            try:
                out_file = Path(output_fn)
                out_file.write_text(out_data)
                try_log(f"Saved output to {output_fn}")
            except Exception:
                try_log(
                    f"Unable to write output to {output_fn}", is_warning=True
                )
                return
        elif dest == lib.OUTPUT_DEST_PAGER:
            output_to_pager(out_data)
        else:
            try_print(out_data)


def read_stdin():
    if sys.stdin.isatty():
        return ""
    return sys.stdin.read().strip()


def get_open_input(string: str):
    if string == "-":
        return read_stdin().strip('"')
    if os.path.exists(string):
        with open(string, "r") as f:
            return f.read().strip().strip('"')
    return string


def handle_list(list_string: str, obj_to_str=None) -> List[str]:
    try:
        objs = None
        try:
            objs = json.loads(list_string)
        except json.JSONDecodeError:
            objs = yaml.load(list_string, yaml.Loader)
            if isinstance(objs, str):
                raise ValueError
        if obj_to_str is not None:
            ret = []
            if isinstance(objs, dict):
                objs = [obj for obj in objs.values()]
            for obj in objs:
                string = obj_to_str(obj)
                if isinstance(string, list):
                    ret.extend(string)
                else:
                    ret.append(string)
            return ret
        return objs
    except Exception:
        return [s.strip().strip('"') for s in list_string.split(",")]


def time_input(args):
    if args.within:
        tup = args.within, int(time.time())
        return tup
    elif args.time_range:
        if args.time_range[1] < args.time_range[0]:
            err_exit("start time was before end time")
        return tuple(args.time_range)
    else:
        t = args.time if args.time else time.time()
        return t, t


def err_exit(message: str, exception: Exception = None):
    lib.err_exit(message, exception)


def output_to_pager(text: str):
    try:
        pipepager(text, cmd="less -R")
    except Exception:
        text = strip_color(text)
        pager(text)


ANSI_ESCAPE = re.compile(
    r"""
    \x1B  # ESC
    (?:   # 7-bit C1 Fe (except CSI)
        [@-Z\\-_]
    |     # or [ for CSI, followed by a control sequence
        \[
        [0-?]*  # Parameter bytes
        [ -/]*  # Intermediate bytes
        [@-~]   # Final byte
    )
    """,
    re.VERBOSE,
)


def strip_color(text: str):
    rv = ANSI_ESCAPE.sub("", text)
    return rv


def _seq_but_not_str(obj):
    return isinstance(obj, Sequence) and not isinstance(
        obj, (str, bytes, bytearray)
    )
