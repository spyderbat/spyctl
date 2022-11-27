import json
import os
import sys
import time
from typing import Callable, Dict, List

import appdirs
import yaml

from spyctl.api import *
from spyctl.args import OUTPUT_JSON, OUTPUT_YAML
from spyctl.fingerprints import Fingerprint

APP_NAME = "spyctl"
APP_AUTHOR = "Spyderbat"
DEFAULT_CONFIG_DIR = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
DEFAULT_CONFIG_FILE = "user_config.yml"
DEFAULT_CONFIG_PATH = os.path.join(DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE)
SELECTED_DEPLOYMENT = None

yaml.Dumper.ignore_aliases = lambda *args: True


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


def contains(obj, filt):
    filt_str = filt.split('=')
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


def try_filter(obj, filt):
    if isinstance(obj, dict):
        remove = []
        for key, val in obj.items():
            try_filter(val, filt)
            if len(val) == 0:
                remove.append(key)
        for key in remove:
            del obj[key]
    elif isinstance(obj, list):
        remove = []
        for i, item in enumerate(obj):
            if not contains(item, filt):
                remove.append(i)
        removed = 0
        for i in remove:
            del obj[i - removed]
            removed += 1


def show(obj, args, alternative_outputs: Dict[str, Callable] = {}):
    for filt in args.filter:
        try_filter(obj, filt)
    if args.output == OUTPUT_YAML:
        try_print(yaml.dump(obj, sort_keys=False), end="")
    elif args.output == OUTPUT_JSON:
        try_print(json.dumps(obj, sort_keys=False, indent=2))
    elif args.output in alternative_outputs:
        try_print(alternative_outputs[args.output](obj), end="")


def read_stdin():
    if sys.stdin.isatty():
        return ""
    return sys.stdin.read().strip()


def get_open_input(string: str):
    if string == "-":
        return read_stdin().strip('"')
    if os.path.exists(string):
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
    elif args.time_range:
        if args.time_range[1] < args.time_range[0]:
            err_exit("start time was before end time")
        return tuple(args.time_range)
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


def clusters_input(args):
    inp = get_open_input(args.clusters)

    def get_uid(clust_obj):
        if 'uid' in clust_obj:
            return clust_obj['uid']
        else:
            err_exit("cluster object input was missing 'uid'")
    names_or_uids = handle_list(inp, get_uid)
    names, uids = get_clusters(*read_config(), api_err_exit)
    clusters = []
    for string in names_or_uids:
        found = False
        for name, uid in zip(names, uids):
            if string == uid or string == name:
                clusters.append({'name': name, 'uid': uid})
                found = True
                break
        if not found:
            err_exit(f"cluster '{string}' did not exist in specified organization")
    clusters.sort(key=lambda c: c['name'])
    return clusters


def machines_input(args):
    inp = get_open_input(args.machines)

    def get_muid(mach):
        if isinstance(mach, list):
            return [get_muid(m) for m in mach]
        elif 'muid' in mach:
            return mach['muid']
        else:
            err_exit("machine object was missing 'muid'")
    names_or_uids = handle_list(inp, get_muid)
    muids, names = get_muids(*read_config(), time_input(args), api_err_exit)
    machs = []
    for string in names_or_uids:
        found = False
        for name, muid in zip(names, muids):
            if string == muid or string == name:
                machs.append({'name': name, 'muid': muid})
                found = True
                break
        if not found:
            err_exit(f"machine '{string}' did not exist in specified organization")
    machs.sort(key=lambda m: m['name'])
    return machs


def pods_input(args):
    inp = get_open_input(args.pods)

    def get_uid(pod_obj):
        if isinstance(pod_obj, list):
            return [get_uid(p) for p in pod_obj]
        elif 'uid' in pod_obj:
            return pod_obj['uid']
        else:
            ret = []
            for sub in pod_obj.values():
                if not isinstance(sub, list):
                    err_exit("pod object was missing 'uid'")
                ret.extend(get_uid(sub))
            return ret
    names_or_uids = handle_list(inp, get_uid)
    _, clus_uids = get_clusters(*read_config(), api_err_exit)
    pods = []
    all_pods = ([], [], [])
    for clus_uid in clus_uids:
        pod_dict = get_clust_pods(*read_config(), clus_uid, time_input(args), api_err_exit)
        for list_tup in pod_dict.values():
            for i in range(len(all_pods)):
                all_pods[i].extend(list_tup[i])
    for string in names_or_uids:
        found = False
        for name, uid, muid in zip(*all_pods):
            if string == name or string == uid:
                pods.append({'name': name, 'uid': uid, 'muid': muid})
                found = True
                break
        if not found:
            try_log(f"pod '{string}' did not exist in specified organization")
            # err_exit(f"pod '{string}' did not exist in specified organization")
    pods.sort(key=lambda p: p['name'])
    return pods


def fingerprint_input(files: List) -> List[Fingerprint]:
    fingerprints = []

    def load_fprint(string):
        try:
            obj = yaml.load(string, yaml.Loader)
            if isinstance(obj, list):
                for o in obj:
                    fingerprints.append(Fingerprint(o))
            else:
                fingerprints.append(Fingerprint(obj))
        except yaml.YAMLError:
            err_exit("invalid yaml input")
        except KeyError as err:
            key, = err.args
            err_exit(f"fingerprint was missing key '{key}'")
    if len(files) == 0:
        inp = read_stdin()
        load_fprint(inp)
    else:
        for file in files:
            load_fprint(file.read())
    return fingerprints


def namespaces_input(args):
    inp = get_open_input(args.namespaces)

    def get_strings(namespace):
        if isinstance(namespace, list):
            return [get_strings(n) for n in namespace]
        else:
            return namespace
    return sorted(handle_list(inp, get_strings))


def set_selected_deployment(deployment: str):
    global SELECTED_DEPLOYMENT
    SELECTED_DEPLOYMENT = deployment


LOADED_DEPLOYMENT = None


def read_config() -> Tuple:
    """Loads the user config from disk and looks for the selected deployment.
    If selected deployment is None loads the default. If no selected deployment
    exists and no default deployment exists, the program exits.

    Returns:
        Tuple: _description_
    """
    global LOADED_DEPLOYMENT
    if LOADED_DEPLOYMENT is None:
        try:
            with open(DEFAULT_CONFIG_PATH, 'r') as f:
                doc = yaml.load(f, yaml.Loader)
                if SELECTED_DEPLOYMENT is not None:
                    try:
                        dplymt = doc[SELECTED_DEPLOYMENT]
                    except KeyError:
                        err_exit(
                            "User configuration missing API information for"
                            f" {SELECTED_DEPLOYMENT} deployment."
                            " Use 'spyctl configure add' to add a deployment.")
                else:
                    dplymt = doc["default"]
                LOADED_DEPLOYMENT = (
                    doc[dplymt]['api_url'],
                    doc[dplymt]['api_key'],
                    doc[dplymt]['org_uid'])
        except (KeyError, OSError):
            err_exit(
                "User configuration missing API information."
                " Use 'spyctl configure' to add or update it")
    return LOADED_DEPLOYMENT


def handle_config_add(args):
    d_name = args.deployment_name
    api_key = args.api_key
    api_url = args.api_url
    org = args.org
    if not os.path.exists(DEFAULT_CONFIG_DIR):
        os.makedirs(DEFAULT_CONFIG_DIR)
    doc = {}
    try:
        with open(DEFAULT_CONFIG_PATH, 'r') as f:
            doc = yaml.load(f, yaml.Loader)
            if doc is None:
                doc = {}
    except OSError:
        pass
    if d_name in doc:
        err_exit("Add unsuccessful, deployment with this name already exists")
    sub = {}
    sub["api_key"] = api_key
    sub["api_url"] = api_url.strip('/')
    try:
        orgs = get_orgs(sub["api_url"], sub["api_key"], try_log)
    except Exception:
        orgs = None
    found = False
    if orgs is not None:
        for uid, name in zip(*orgs):
            if org == name or org == uid:
                if name == "Defend The Flag":
                    err_exit("invalid organization")
                sub["org_uid"] = uid
                found = True
                break
    if not found:
        try_log("\nWarning: unable to verify organization for specified API key and url\n")
        sub["org_uid"] = org
    if "default" not in doc or args.set_default:
        try_log(f"Updated default configuration")
        doc["default"] = sub
    doc[d_name] = sub
    with open(DEFAULT_CONFIG_PATH, 'w') as f:
        yaml.dump(doc, f)
    try_log(f"Added {d_name} deployment to {DEFAULT_CONFIG_PATH}")


def handle_config_update(args):
    d_name = args.deployment_name
    api_key = args.api_key
    api_url = args.api_url
    org = args.org
    if (not os.path.exists(DEFAULT_CONFIG_PATH)
            or not os.path.isfile(DEFAULT_CONFIG_PATH)):
        err_exit(
            "User configuration does not exist, no deployments to update,"
            " use 'spyctl config add'")
    doc = {}
    try:
        with open(DEFAULT_CONFIG_PATH, 'r') as f:
            doc = yaml.load(f, yaml.Loader)
            if doc is None:
                doc = {}
    except IOError:
        err_exit("Unable to open user configuration file")
    except Exception:
        pass
    if d_name not in doc:
        err_exit(
            f"Unable to update deployment, '{d_name}' not in user"
            " configuration file")
    sub = {}
    sub["api_key"] = api_key if api_key is not None \
        else doc[d_name]["api_key"]
    sub["api_url"] = api_url.strip('/') if api_url is not None \
        else doc[d_name]["api_url"]
    uid = org if org is not None else doc[d_name]["org_uid"]
    if org is not None:
        try:
            orgs = get_orgs(sub["api_url"], sub["api_key"], try_log)
        except Exception:
            orgs = None
        found = False
        if orgs is not None:
            for uid, name in zip(*orgs):
                if org == name or org == uid:
                    if name == "Defend The Flag":
                        err_exit("invalid organization")
                    sub["org_uid"] = uid
                    found = True
                    break
        if not found:
            try_log("\nWarning: unable to verify organization for specified API key and url\n")
            sub["org_uid"] = org
    else:
        sub["org_uid"] = uid
    if "default" not in doc or args.set_default:
        try_log(f"Updated default configuration")
        doc["default"] = sub
    doc[d_name] = sub
    with open(DEFAULT_CONFIG_PATH, 'w') as f:
        yaml.dump(doc, f)
    try_log(f"Updated {d_name} deployment")


def handle_config_setdefault(args):
    d_name = args.deployment_name
    if (not os.path.exists(DEFAULT_CONFIG_PATH)
            or not os.path.isfile(DEFAULT_CONFIG_PATH)):
        err_exit(
            "User configuration does not exist, no deployments to update,"
            " use 'spyctl config add'")
    doc = {}
    try:
        with open(DEFAULT_CONFIG_PATH, 'r') as f:
            doc = yaml.load(f, yaml.Loader)
            if doc is None:
                doc = {}
    except IOError:
        err_exit("Unable to open user configuration file")
    except Exception:
        pass
    if d_name not in doc:
        err_exit(
            f"Unable to set deployment as default, '{d_name}' not in user"
            " configuration file")
    doc["default"] = doc[d_name]
    with open(DEFAULT_CONFIG_PATH, 'w') as f:
        yaml.dump(doc, f)
    try_log(f"Set {d_name} as default deployment")


def handle_config_delete(args):
    d_name = args.deployment_name
    if (not os.path.exists(DEFAULT_CONFIG_PATH)
            or not os.path.isfile(DEFAULT_CONFIG_PATH)):
        err_exit(
            "User configuration does not exist, no deployments to update,"
            " use 'spyctl config add'")
    doc = {}
    try:
        with open(DEFAULT_CONFIG_PATH, 'r') as f:
            doc = yaml.load(f, yaml.Loader)
            if doc is None:
                doc = {}
    except IOError:
        err_exit("Unable to open user configuration file")
    except Exception:
        pass
    if d_name not in doc:
        err_exit(
            f"Unable to delete deployment, '{d_name}' not in user"
            " configuration file")
    del doc[d_name]
    with open(DEFAULT_CONFIG_PATH, 'w') as f:
        yaml.dump(doc, f)
    try_log(f"Deleted {d_name} deployment from configuration file")


def handle_config_show(args):
    if (not os.path.exists(DEFAULT_CONFIG_PATH)
            or not os.path.isfile(DEFAULT_CONFIG_PATH)):
        err_exit(
            "User configuration does not exist, no deployments to update,"
            " use 'spyctl config add'")
    doc = {}
    try:
        with open(DEFAULT_CONFIG_PATH, 'r') as f:
            doc = yaml.load(f, yaml.Loader)
            if doc is None:
                doc = {}
    except IOError:
        err_exit("Unable to open user configuration file")
    except Exception:
        pass
    if len(doc) == 0:
        try_print(
            "No deployments loaded in configuration, use"
            " 'spyctl config add' to add a deployment")
    else:
        try_print(yaml.dump(doc, sort_keys=False), end="")
