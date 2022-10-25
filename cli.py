from genericpath import exists
import os, sys
import time
from typing import List
import yaml, json
from api import *


CONFIG_PATH = "./config.yml"


def try_log(*args, **kwargs):
    try:
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


def contains(obj, args):
    filt_str = args.filter.split('=')
    keys = []
    if len(filt_str) > 1:
        keys = filt_str[0].split('.')
    val_str = filt_str[-1]
    def cont_keys(obj, keys):
        if isinstance(obj, dict):
            # returns false if it doesn't have the key
            for key, val in obj.items():
                if len(keys) > 0 and keys[0] != key:
                    continue
                if cont_keys(val, keys[1:]):
                    return True
            return False
        elif isinstance(obj, str):
            return val_str in obj
        return True
    return cont_keys(obj, keys)


def try_filter(obj, args):
    if isinstance(obj, dict):
        remove = []
        for key, val in obj.items():
            try_filter(val, args)
            if len(val) == 0:
                remove.append(key)
        for key in remove:
            del obj[key]
    elif isinstance(obj, list):
        remove = []
        for i, item in enumerate(obj):
            if not contains(item, args):
                remove.append(i)
        removed = 0
        for i in remove:
            del obj[i - removed]
            removed += 1


def show(obj, args):
    if args.filter:
        try_filter(obj, args)
    if args.output == "yaml":
        try_print(yaml.dump(obj, sort_keys=False), end="")
    elif args.output == "json":
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


def time_input(args):
    if args.within:
        tup = args.within, int(time.time())
        return tup
    else:
        t = args.time if args.time else time.time()
        return t, t


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
            dplymt = doc.get("deployment", "default")
            return doc[dplymt]['api_url'], \
                doc[dplymt]['api_key'], \
                doc[dplymt]['org_uid']
    except (KeyError, OSError):
        err_exit("config was missing API information. use 'spyctl configure' to add or update it")
