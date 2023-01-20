import json
import os
import sys
import time
from typing import Callable, Dict, List

import yaml

import spyctl.resources.policies as p
import spyctl.spyctl_lib as lib
import spyctl.config.configs as u_conf
import spyctl.api as api

from spyctl.resources.fingerprints import Fingerprint

yaml.Dumper.ignore_aliases = lambda *args: True

WARNING_MSG = "is_warning"
WARNING_COLOR = "\033[38;5;203m"
COLOR_END = "\033[0m"


def try_log(*args, **kwargs):
    try:
        if kwargs.pop(WARNING_MSG, False):
            msg = f"{WARNING_COLOR}{' '.join(args)}{COLOR_END}"
            print(msg, **kwargs, file=sys.stderr)
        else:
            print(*args, **kwargs, file=sys.stderr)
        sys.stderr.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stderr.fileno())
        sys.exit(1)


def try_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
        sys.stdout.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(1)


def unsupported_output_msg(output: str, command: str = None) -> str:
    if command is None:
        command = lib.get_click_command()
    return f"--output {output} is not supported for {command}."


YES_OPTION = False


def set_yes_option():
    global YES_OPTION
    YES_OPTION = True


def query_yes_no(question, default="yes"):
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
        if YES_OPTION:
            return True
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write(
                "Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n"
            )


def show(obj, output, alternative_outputs: Dict[str, Callable] = {}):
    if output == lib.OUTPUT_YAML:
        try_print(yaml.dump(obj, sort_keys=False), end="")
    elif output == lib.OUTPUT_JSON:
        try_print(json.dumps(obj, sort_keys=False, indent=2))
    elif output == lib.OUTPUT_RAW:
        try_print(obj)
    elif output in alternative_outputs:
        try_print(alternative_outputs[output](obj))
    else:
        err_exit(unsupported_output_msg(output))


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


def err_exit(message: str):
    sys.exit(f"{WARNING_COLOR}Error: {message}{COLOR_END}\n")
