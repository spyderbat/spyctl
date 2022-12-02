import appdirs
from typing import Dict, List, Tuple
import os
import yaml
import spyctl.cli as cli
import spyctl.get as get
import spyctl.api as api

APP_NAME = "spyctl"
APP_AUTHOR = "Spyderbat"
DEFAULT_CONFIG_DIR = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
DEFAULT_CONFIG_FILE = "user_config.yml"
DEFAULT_CONFIG_PATH = os.path.join(DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_FILE)
SELECTED_DEPLOYMENT = None
LOADED_DEPLOYMENT = None


def set_selected_deployment(deployment: str):
    global SELECTED_DEPLOYMENT
    SELECTED_DEPLOYMENT = deployment


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
            with open(DEFAULT_CONFIG_PATH, "r") as f:
                doc = yaml.load(f, yaml.Loader)
                if SELECTED_DEPLOYMENT is not None:
                    try:
                        dplymt = doc[SELECTED_DEPLOYMENT]
                    except KeyError:
                        cli.err_exit(
                            "User configuration missing for"
                            f" '{SELECTED_DEPLOYMENT}' deployment."
                            " Use 'spyctl configure add' to add a deployment."
                        )
                else:
                    dplymt = doc["default"]
                LOADED_DEPLOYMENT = (
                    dplymt["api_url"],
                    dplymt["api_key"],
                    dplymt["org_uid"],
                )
        except (KeyError, OSError):
            cli.err_exit(
                "User configuration missing."
                " Use 'spyctl configure' to add or update it"
            )
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
        with open(DEFAULT_CONFIG_PATH, "r") as f:
            doc = yaml.load(f, yaml.Loader)
            if doc is None:
                doc = {}
    except OSError:
        pass
    if d_name in doc:
        cli.err_exit(
            "Add unsuccessful, deployment with this name already exists"
        )
    sub = {}
    sub["api_key"] = api_key
    sub["api_url"] = api_url.strip("/")
    try:
        orgs = api.get_orgs(sub["api_url"], sub["api_key"], cli.try_log)
    except Exception:
        orgs = None
    found = False
    if orgs is not None:
        for uid, name in zip(*orgs):
            if org == name or org == uid:
                if name == "Defend The Flag":
                    cli.err_exit("invalid organization")
                sub["org_uid"] = uid
                found = True
                break
    if not found:
        cli.try_log(
            "\nWarning: unable to verify organization for specified API key"
            " and url\n"
        )
        sub["org_uid"] = org
    if "default" not in doc or args.set_default:
        cli.try_log(f"Updated default configuration")
        doc["default"] = sub
    doc[d_name] = sub
    with open(DEFAULT_CONFIG_PATH, "w") as f:
        yaml.dump(doc, f)
    cli.try_log(f"Added {d_name} deployment to {DEFAULT_CONFIG_PATH}")


def handle_config_update(args):
    d_name = args.deployment_name
    api_key = args.api_key
    api_url = args.api_url
    org = args.org
    if not os.path.exists(DEFAULT_CONFIG_PATH) or not os.path.isfile(
        DEFAULT_CONFIG_PATH
    ):
        cli.err_exit(
            "User configuration does not exist, no deployments to update,"
            " use 'spyctl config add'"
        )
    doc = {}
    try:
        with open(DEFAULT_CONFIG_PATH, "r") as f:
            doc = yaml.load(f, yaml.Loader)
            if doc is None:
                doc = {}
    except IOError:
        cli.err_exit("Unable to open user configuration file")
    except Exception:
        pass
    if d_name not in doc:
        cli.err_exit(
            f"Unable to update deployment, '{d_name}' not in user"
            " configuration file"
        )
    sub = {}
    sub["api_key"] = api_key if api_key is not None else doc[d_name]["api_key"]
    sub["api_url"] = (
        api_url.strip("/") if api_url is not None else doc[d_name]["api_url"]
    )
    uid = org if org is not None else doc[d_name]["org_uid"]
    if org is not None:
        try:
            orgs = api.get_orgs(sub["api_url"], sub["api_key"], cli.try_log)
        except Exception:
            orgs = None
        found = False
        if orgs is not None:
            for uid, name in zip(*orgs):
                if org == name or org == uid:
                    if name == "Defend The Flag":
                        cli.err_exit("invalid organization")
                    sub["org_uid"] = uid
                    found = True
                    break
        if not found:
            cli.try_log(
                "\nWarning: unable to verify organization for specified API"
                " key and url\n"
            )
            sub["org_uid"] = org
    else:
        sub["org_uid"] = uid
    if "default" not in doc or args.set_default:
        cli.try_log(f"Updated default configuration")
        doc["default"] = sub
    doc[d_name] = sub
    with open(DEFAULT_CONFIG_PATH, "w") as f:
        yaml.dump(doc, f)
    cli.try_log(f"Updated {d_name} deployment")


def handle_config_setdefault(args):
    d_name = args.deployment_name
    if not os.path.exists(DEFAULT_CONFIG_PATH) or not os.path.isfile(
        DEFAULT_CONFIG_PATH
    ):
        cli.err_exit(
            "User configuration does not exist, no deployments to update,"
            " use 'spyctl config add'"
        )
    doc = {}
    try:
        with open(DEFAULT_CONFIG_PATH, "r") as f:
            doc = yaml.load(f, yaml.Loader)
            if doc is None:
                doc = {}
    except IOError:
        cli.err_exit("Unable to open user configuration file")
    except Exception:
        pass
    if d_name not in doc:
        cli.err_exit(
            f"Unable to set deployment as default, '{d_name}' not in user"
            " configuration file"
        )
    doc["default"] = doc[d_name]
    with open(DEFAULT_CONFIG_PATH, "w") as f:
        yaml.dump(doc, f)
    cli.try_log(f"Set {d_name} as default deployment")


def handle_config_delete(args):
    d_name = args.deployment_name
    if not os.path.exists(DEFAULT_CONFIG_PATH) or not os.path.isfile(
        DEFAULT_CONFIG_PATH
    ):
        cli.err_exit(
            "User configuration does not exist, no deployments to update,"
            " use 'spyctl config add'"
        )
    doc = {}
    try:
        with open(DEFAULT_CONFIG_PATH, "r") as f:
            doc = yaml.load(f, yaml.Loader)
            if doc is None:
                doc = {}
    except IOError:
        cli.err_exit("Unable to open user configuration file")
    except Exception:
        pass
    if d_name not in doc:
        cli.err_exit(
            f"Unable to delete deployment, '{d_name}' not in user"
            " configuration file"
        )
    del doc[d_name]
    with open(DEFAULT_CONFIG_PATH, "w") as f:
        yaml.dump(doc, f)
    cli.try_log(f"Deleted {d_name} deployment from configuration file")


def handle_config_show(args):
    if not os.path.exists(DEFAULT_CONFIG_PATH) or not os.path.isfile(
        DEFAULT_CONFIG_PATH
    ):
        cli.err_exit(
            "User configuration does not exist, no deployments to update,"
            " use 'spyctl config add'"
        )
    doc = {}
    try:
        with open(DEFAULT_CONFIG_PATH, "r") as f:
            doc = yaml.load(f, yaml.Loader)
            if doc is None:
                doc = {}
    except IOError:
        cli.err_exit("Unable to open user configuration file")
    except Exception:
        pass
    if len(doc) == 0:
        cli.try_print(
            "No deployments loaded in configuration, use"
            " 'spyctl config add' to add a deployment"
        )
    else:
        cli.try_print(yaml.dump(doc, sort_keys=False), end="")
