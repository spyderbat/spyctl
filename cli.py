from genericpath import exists
import os, sys, subprocess
from typing import List
import yaml, json
from api import *


CONFIG_PATH = "./config.yml"


def try_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
        sys.stdout.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(1)


def show(obj, output):
    if output == "yaml":
        try_print(yaml.dump(obj, sort_keys=False), end="")
    elif output == "json":
        try_print(json.dumps(obj, sort_keys=False, indent=2))
        # try_print(json.dumps(obj, sort_keys=False))


def read_stdin():
    if sys.stdin.isatty():
        return ""
    return sys.stdin.read().strip()


def get_open_input(string: str):
    if string == "-":
        return read_stdin().strip('"')
    if exists(string):
        with open(string, 'r') as f:
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


def err_exit(message: str):
    sys.stderr.write(f"Error: {message}\n")
    exit(1)


def api_err_exit(error_code, reason, msg=None):
    title = f"{error_code} ({reason}) error while fetching data"
    if msg is not None:
        title += ". " + msg
    err_exit(title)


def read_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            doc = yaml.load(f, yaml.Loader)
            dplymt = doc['deployment']
            return doc[dplymt]['api_url'], \
                doc[dplymt]['api_key'], \
                doc[dplymt]['org_uid']
    except (KeyError, OSError):
        err_exit("config was missing API information. use 'prints configure' to add or update it")
