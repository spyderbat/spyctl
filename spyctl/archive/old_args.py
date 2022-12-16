from __future__ import annotations

import time
from argparse import *
from argparse import _SubParsersAction
from datetime import datetime
from typing import Dict

import dateutil.parser as dateparser

from spyctl.resources.fingerprints import FPRINT_TYPE_CONT, FPRINT_TYPE_SVC
from spyctl.spyctl_lib import *

OUTPUT_YAML = "yaml"
OUTPUT_JSON = "json"
OUTPUT_SUMMARY = "summary"
OUTPUT_DEFAULT = OUTPUT_YAML
OUTPUT_CHOICES = [OUTPUT_JSON, OUTPUT_YAML]
DEFAULT_API_URL = "https://api.prod.spyderbat.com"
SP_POL_NAMES_AND_ALIASES = [
    "spyderbat-policy",
    "spyderbat-policies",
    "spy-pol",
    "spol",
    "sp",
]
UPLOAD_NAMES_AND_ALIASES = ["upload", "push"]
DELETE_NAMES_AND_ALIASES = ["delete", "del"]


class CustomHelpFormatter(RawDescriptionHelpFormatter):
    def _format_action_invocation(self, action):
        # changes "-p PODS, --pods PODS" tp "-p, --pods PODS"
        if action.option_strings:
            default = self._get_default_metavar_for_optional(action)
            args_string = self._format_args(action, default)
            return ", ".join(action.option_strings) + " " + args_string
        # changes subcommands "{get,merge,compare}" to "get, merge, compare"
        # and removes aliases from the list
        elif action.choices is not None and action.metavar is None:
            choice_strs = []
            try:
                obj_set = set()
                for choice, obj in action.choices.items():
                    if obj not in obj_set:
                        obj_set.add(obj)
                        choice_strs.append(str(choice))
            except AttributeError:
                choice_strs = [str(choice) for choice in action.choices]
            return ", ".join(choice_strs)
        else:
            return super()._format_action_invocation(action)

    def _format_args(self, action: Action, default_metavar: str) -> str:
        # changes "[files [files ...]]" to "[files ...]"
        if action.nargs == ZERO_OR_MORE:
            get_metavar = self._metavar_formatter(action, default_metavar)
            return "[%s ...]" % get_metavar(1)
        # changes "files [files ...]" to "files [...]"
        elif action.nargs == ONE_OR_MORE:
            get_metavar = self._metavar_formatter(action, default_metavar)
            return "%s [...]" % get_metavar(1)
        return super()._format_args(action, default_metavar)

    def _metavar_formatter(self, action: Action, default_metavar: str):
        # removes aliases
        if action.metavar is None and action.choices is not None:
            choice_strs = []
            try:
                obj_set = set()
                for choice, obj in action.choices.items():
                    if obj not in obj_set:
                        obj_set.add(obj)
                        choice_strs.append(str(choice))
            except AttributeError:
                choice_strs = [str(choice) for choice in action.choices]
            result = "{%s}" % ",".join(choice_strs)
            return lambda size: (result,) * size
        return super()._metavar_formatter(action, default_metavar)


# create a keyvalue class
# https://www.geeksforgeeks.org/python-key-value-pair-using-argparse/
class keyvalue(Action):
    # Constructor calling
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, dict())

        for value in values:
            # split it into key and value
            key, value = value.split("=")
            # assign into dictionary
            getattr(namespace, self.dest)[key] = value


def fmt(prog):
    return CustomHelpFormatter(prog)


def time_inp(time_str: str) -> int:
    past_seconds = 0
    try:
        try:
            past_seconds = int(time_str) * 60
        except ValueError:
            if time_str.endswith(("s", "sc")):
                past_seconds = int(time_str[:-1])
            elif time_str.endswith(("m", "mn")):
                past_seconds = int(time_str[:-1]) * 60
            elif time_str.endswith(("h", "hr")):
                past_seconds = int(time_str[:-1]) * 60 * 60
            elif time_str.endswith(("d", "dy")):
                past_seconds = int(time_str[:-1]) * 60 * 60 * 24
            elif time_str.endswith(("w", "wk")):
                past_seconds = int(time_str[:-1]) * 60 * 60 * 24 * 7
            else:
                date = dateparser.parse(time_str)
                diff = datetime.now() - date
                past_seconds = diff.total_seconds()
    except (ValueError, dateparser.ParserError):
        raise ValueError("invalid time input (see global help menu)") from None
    if past_seconds < 0:
        raise ValueError("time must be in the past")
    return int(time.time() - past_seconds)


command_names = {}


def name_and_aliases(names):
    command_names[names[0]] = names
    if len(names) == 0:
        return dict(name=names[0])
    return dict(name=names[0], aliases=names[1:])


def get_names(command):
    return command_names.get(command, command)


def add_output_arg(parser, output_choices=OUTPUT_CHOICES):
    parser.add_argument(
        "-o",
        "--output",
        choices=output_choices,
        type=output_argument_helper,
        default=OUTPUT_DEFAULT,
    )
    parser.add_argument(
        "-f",
        "--filter",
        help="filter output objects by string",
        action="append",
        default=[],
    )


def add_policy_file_arg(parser: ArgumentParser):
    parser.add_argument(
        "file",
        help="file containing spyderbat policy",
        type=FileType("r"),
        nargs="?",
    )


def output_argument_helper(input: str) -> str:
    i = input.lower()
    if i.startswith("y"):
        return OUTPUT_YAML
    elif i.startswith("j"):
        return OUTPUT_JSON
    elif i.startswith("s"):
        return OUTPUT_SUMMARY
    else:
        return i


def add_time_arg(parser):
    times = parser.add_mutually_exclusive_group()
    times.add_argument(
        "-t", "--time", help="collect data at this time", type=time_inp
    )
    times.add_argument(
        "-r",
        "--time-range",
        help="collect data between two times",
        action="extend",
        nargs=2,
        type=time_inp,
    )
    times.add_argument(
        "-w",
        "--within",
        help="collect data from this time until now",
        metavar="TIME",
        type=time_inp,
    )


def parse_args():
    desc = "a tool to help manage Spyderbat fingerprints and policies"
    epilog = "see TUTORIAL.md for an explanation of usage"
    parser = ArgumentParser(
        description=desc, epilog=epilog, formatter_class=fmt
    )
    parser.add_argument(
        "--deployment",
        help="name of deployment to use from user configuration file",
        dest="selected_deployment",
    )
    parser.add_argument(
        "-y",
        "--yes",
        help="automatic yes to prompts; assume 'yes' as answer to all prompts"
        " and run non-interactively.",
        action="store_true",
    )
    subs = parser.add_subparsers(
        title="subcommands", dest="subcommand", required=True
    )
    make_compare(subs)
    make_configure(subs)
    make_create(subs)
    make_delete(subs)
    make_get(subs)
    make_manage(subs)
    make_merge(subs)
    make_upload(subs)
    return parser.parse_args()


def make_configure(subs: _SubParsersAction[ArgumentParser]):
    desc = "configure API information"
    names = ["configure", "conf", "config"]
    configure = subs.add_parser(
        **name_and_aliases(names), description=desc, formatter_class=fmt
    )
    configure_subs = configure.add_subparsers(
        title="configure commands", dest="config_cmd"
    )
    make_configure_add(configure_subs)
    make_configure_update(configure_subs)
    make_configure_setdefault(configure_subs)
    make_configure_delete(configure_subs)
    make_configure_show(configure_subs)


def make_configure_add(configure_subs: _SubParsersAction[ArgumentParser]):
    desc = "add Spyderbat API deployment to spyctl user configuration"
    configure_add = configure_subs.add_parser(
        "add", description=desc, formatter_class=fmt
    )
    configure_add.add_argument(
        "deployment_name", help="the name of the deployment to add"
    )
    configure_add.add_argument("-k", "--api_key", metavar="KEY", required=True)
    configure_add.add_argument(
        "-u",
        "--api_url",
        help=f"Default: {DEFAULT_API_URL}",
        default=DEFAULT_API_URL,
        metavar="URL",
    )
    configure_add.add_argument(
        "-o", "--org", metavar="NAME_OR_UID", required=True
    )
    configure_add.add_argument(
        "-D",
        "--set-default",
        action="store_true",
        help="set config as default",
    )


def make_configure_update(configure_subs: _SubParsersAction[ArgumentParser]):
    desc = (
        "update a specific Spyderbat API deployment in spyctl user"
        " configuration"
    )
    configure_update = configure_subs.add_parser(
        "update", description=desc, formatter_class=fmt
    )
    configure_update.add_argument(
        "deployment_name", help="the name of the deployment to update"
    )
    configure_update.add_argument("-k", "--api_key", metavar="KEY")
    configure_update.add_argument("-u", "--api_url", metavar="URL")
    configure_update.add_argument("-o", "--org", metavar="NAME_OR_UID")
    configure_update.add_argument(
        "-D",
        "--set-default",
        action="store_true",
        help="set deployment as default",
    )


def make_configure_setdefault(
    configure_subs: _SubParsersAction[ArgumentParser],
):
    desc = (
        "set a Spyderbat API deployment as default in spyctl user",
        " configuration",
    )
    configure_default = configure_subs.add_parser(
        "default", description=desc, formatter_class=fmt
    )
    configure_default.add_argument(
        "deployment_name", help="the name of the deployment to set as default"
    )


def make_configure_delete(configure_subs: _SubParsersAction[ArgumentParser]):
    desc = "delete a Spyderbat API deployment from spyctl user configuration"
    configure_delete = configure_subs.add_parser(
        "delete", description=desc, formatter_class=fmt
    )
    configure_delete.add_argument(
        "deployment_name", help="the name of the deployment to set as default"
    )


def make_configure_show(configure_subs: _SubParsersAction[ArgumentParser]):
    desc = "show the user configuration file"
    configure_show = configure_subs.add_parser(
        "show", description=desc, formatter_class=fmt
    )


def make_delete(subs: _SubParsersAction[ArgumentParser]):
    desc = "Delete Spyderbat objects"
    names = DELETE_NAMES_AND_ALIASES
    delete = subs.add_parser(
        **name_and_aliases(DELETE_NAMES_AND_ALIASES),
        description=desc,
        formatter_class=fmt,
    )
    delete_subs = delete.add_subparsers(
        title="delete commands", dest="delete_cmd"
    )
    make_delete_policy(SP_POL_NAMES_AND_ALIASES, delete_subs)


def make_delete_policy(names, delete_subs: _SubParsersAction[ArgumentParser]):
    desc = "Delete Spyderbat policy via API call"
    delete_policy = delete_subs.add_parser(
        **name_and_aliases(names), description=desc, formatter_class=fmt
    )
    del_pol_grp = delete_policy.add_mutually_exclusive_group(required=True)
    del_pol_grp.add_argument(
        "-u", "--uid", help="UID of Spyderbat Policy object"
    )
    del_pol_grp.add_argument(
        "-P",
        "--policy",
        help="Spyderbat Policy with uid in metadata field",
        dest="policy_file",
    )


def make_manage(subs: _SubParsersAction[ArgumentParser]):
    desc = "Edit Spyderbat objects"
    manage = subs.add_parser("manage", description=desc, formatter_class=fmt)
    manage_subs = manage.add_subparsers(
        title="manage commands", dest="manage_cmd"
    )
    make_manage_policy(manage_subs)


def make_manage_policy(manage_subs: _SubParsersAction[ArgumentParser]):
    desc = "Manage Spyderbat policy objects"
    names = SP_POL_NAMES_AND_ALIASES
    manage_policy = manage_subs.add_parser(
        **name_and_aliases(names), description=desc, formatter_class=fmt
    )
    man_pol_subs = manage_policy.add_subparsers(
        title="policy management commands", dest="pol_cmd"
    )
    make_manage_policy_add_response(man_pol_subs)
    make_manage_policy_enable(man_pol_subs)
    make_manage_policy_disable(man_pol_subs)
    make_upload_policy(UPLOAD_NAMES_AND_ALIASES, man_pol_subs)
    make_delete_policy(DELETE_NAMES_AND_ALIASES, man_pol_subs)


def make_manage_policy_add_response(
    man_pol_subs: _SubParsersAction[ArgumentParser],
):
    desc = "Add a response action to a Spyderbat policy object"
    man_pol_add_resp = man_pol_subs.add_parser(
        "add-response", description=desc, formatter_class=fmt
    )
    add_policy_file_arg(man_pol_add_resp)
    man_pol_add_resp.add_argument(
        "-s",
        "--severity",
        choices=ALLOWED_SEVERITIES,
        help="severity of spyderbat flag for matching policy deviation",
    )
    man_pol_add_resp.add_argument(
        "-a",
        "--action",
        choices=ALLOWED_ACTIONS,
        help="the type of response action to be taken",
        required=True,
    )
    man_pol_add_resp.add_argument(
        "-p",
        "--pod-labels",
        metavar="POD_LABEL",
        help="key=value pairs separated by space for use in matching against"
        " k8s pod labels (ex. 'env=prod app=website)'",
        nargs="*",
        action=keyvalue,
    )
    man_pol_add_resp.add_argument(
        "-n",
        "--namespace-labels",
        metavar="NAMESPACE_LABEL",
        help="key=value pairs separated by space for use in matching against"
        " k8s namespace labels (ex. 'env=prod app=website')",
        nargs="*",
        action=keyvalue,
    )
    add_output_arg(man_pol_add_resp)
    webhook_group_desc = f"options required when action is '{ACTION_WEBHOOK}'"
    webhook_group = man_pol_add_resp.add_argument_group(
        "webhook arguments", webhook_group_desc
    )
    webhook_group.add_argument(
        "-t",
        "--template",
        choices=ALLOWED_TEMPLATES,
        help="the structure of the webhook output",
    )
    webhook_group.add_argument(
        "-u",
        "--url",
        help="url destination for the webhook",
    )


def make_manage_policy_enable(
    man_pol_subs: _SubParsersAction[ArgumentParser],
):
    desc = (
        "Enable a Spyderbat policy object\n  note: policies are enabled by"
        " default"
    )
    man_pol_enable = man_pol_subs.add_parser(
        "enable", description=desc, formatter_class=fmt
    )
    add_policy_file_arg(man_pol_enable)
    add_output_arg(man_pol_enable)


def make_manage_policy_disable(
    man_pol_subs: _SubParsersAction[ArgumentParser],
):
    desc = (
        "Disable a Spyderbat policy object\n  note: this adds an"
        f" '{ENABLED_FIELD}: false' field to the policy object."
        " The policy must be uploaded for this to take effect"
    )
    man_pol_disable = man_pol_subs.add_parser(
        "disable", description=desc, formatter_class=fmt
    )
    add_policy_file_arg(man_pol_disable)
    add_output_arg(man_pol_disable)


def make_create(subs: _SubParsersAction[ArgumentParser]):
    desc = "create YAML objects for use in Spyderbat"
    create = subs.add_parser("create", description=desc, formatter_class=fmt)
    create_subs = create.add_subparsers(
        title="output objects", dest="create_target"
    )
    make_create_spyderbat_policy(create_subs)


def make_create_spyderbat_policy(
    create_subs: _SubParsersAction[ArgumentParser],
):
    names = SP_POL_NAMES_AND_ALIASES
    create_spyderbat_policy = create_subs.add_parser(
        **name_and_aliases(names), formatter_class=fmt
    )
    create_spyderbat_policy.add_argument(
        "-F",
        "--fingerprints",
        help="fingerprint(s) to build a policy from",
        nargs="?",
        const="-",
    )
    create_spyderbat_policy.add_argument(
        "type",
        choices=[POL_TYPE_CONT, POL_TYPE_SVC],
        help="the type of policy to create",
    )
    add_output_arg(create_spyderbat_policy)


def make_get(subs: _SubParsersAction[ArgumentParser]):
    desc = "get different types of information and objects"
    names = ["get", "pull"]
    get = subs.add_parser(
        **name_and_aliases(names), description=desc, formatter_class=fmt
    )
    get_subs = get.add_subparsers(title="targets", dest="get_target")
    make_get_cluster(get_subs)
    make_get_namespace(get_subs)
    make_get_machine(get_subs)
    make_get_pod(get_subs)
    make_get_fingerprint(get_subs)
    make_get_policy(get_subs)


def make_get_cluster(get_subs: _SubParsersAction[ArgumentParser]):
    names = ["clusters", "clust", "clusts", "cluster"]
    get_cluster = get_subs.add_parser(
        **name_and_aliases(names), formatter_class=fmt
    )
    add_time_arg(get_cluster)
    add_output_arg(get_cluster)


def make_get_namespace(get_subs: _SubParsersAction[ArgumentParser]):
    names = ["namespaces", "name", "names", "namesp", "namesps", "namespace"]
    get_namespace = get_subs.add_parser(
        **name_and_aliases(names), formatter_class=fmt
    )
    get_namespace.add_argument(
        "-c", "--clusters", nargs="?", const="-", required=True
    )
    add_time_arg(get_namespace)
    add_output_arg(get_namespace)


def make_get_machine(get_subs: _SubParsersAction[ArgumentParser]):
    names = ["machines", "mach", "machs", "machine"]
    get_machine = get_subs.add_parser(
        **name_and_aliases(names), formatter_class=fmt
    )
    get_machine.add_argument("-c", "--clusters", nargs="?", const="-")
    add_time_arg(get_machine)
    add_output_arg(get_machine)


def make_get_pod(get_subs: _SubParsersAction[ArgumentParser]):
    names = ["pods", "pod"]
    get_pod = get_subs.add_parser(
        **name_and_aliases(names), formatter_class=fmt
    )
    get_pod.add_argument("-c", "--clusters", nargs="?", const="-")
    get_pod.add_argument("-m", "--machines", nargs="?", const="-")
    get_pod.add_argument("-n", "--namespaces", nargs="?", const="-")
    add_time_arg(get_pod)
    add_output_arg(get_pod)


def make_get_fingerprint(get_subs: _SubParsersAction[ArgumentParser]):
    names = ["fingerprints", "print", "prints", "fingerprint"]
    get_fingerprint = get_subs.add_parser(
        **name_and_aliases(names), formatter_class=fmt
    )
    get_fingerprint.add_argument(
        "type",
        choices=[FPRINT_TYPE_CONT, FPRINT_TYPE_SVC],
        help="the type of fingerprints to get",
    )
    selector_group = get_fingerprint.add_mutually_exclusive_group()
    selector_group.add_argument("-c", "--clusters", nargs="?", const="-")
    selector_group.add_argument("-m", "--machines", nargs="?", const="-")
    selector_group.add_argument("-p", "--pods", nargs="?", const="-")
    add_time_arg(get_fingerprint)
    output_choices = OUTPUT_CHOICES + [OUTPUT_SUMMARY]
    add_output_arg(get_fingerprint, output_choices)


def make_get_policy(get_subs: _SubParsersAction[ArgumentParser]):
    names = SP_POL_NAMES_AND_ALIASES
    get_policy = get_subs.add_parser(
        **name_and_aliases(names), formatter_class=fmt
    )
    get_policy.add_argument(
        "type",
        choices=[POL_TYPE_CONT, POL_TYPE_SVC],
        help="the type of policy to get",
    )
    pol_uid_grp = get_policy.add_mutually_exclusive_group()
    pol_uid_grp.add_argument(
        "-u", "--uid", help="UID of Spyderbat Policy object"
    )
    pol_uid_grp.add_argument(
        "-P",
        "--policy",
        help="Spyderbat Policy with uid in metadata field",
        dest="policy_file",
    )
    add_output_arg(get_policy)


def make_compare(subs: _SubParsersAction[ArgumentParser]):
    desc = "compare a set of fingerprints"
    names = ["compare", "diff", "comp"]
    compare = subs.add_parser(
        **name_and_aliases(names), description=desc, formatter_class=fmt
    )
    compare.add_argument(
        "files",
        help="fingerprint files to compare",
        type=FileType("r"),
        nargs="*",
    )


def make_merge(subs: _SubParsersAction[ArgumentParser]):
    desc = "merge a set of fingerprints"
    names = ["merge", "combine"]
    merge = subs.add_parser(
        **name_and_aliases(names), description=desc, formatter_class=fmt
    )
    merge.add_argument(
        "files",
        help="fingerprint files to merge",
        type=FileType("r"),
        nargs="*",
    )
    add_output_arg(merge)


def make_upload(subs: _SubParsersAction[ArgumentParser]):
    desc = "Upload an object to Spyderbat's backend"
    names = UPLOAD_NAMES_AND_ALIASES
    upload = subs.add_parser(
        **name_and_aliases(names), description=desc, formatter_class=fmt
    )
    upload_subs = upload.add_subparsers(
        title="upload commands", description=desc, dest="upload_cmd"
    )
    make_upload_policy(SP_POL_NAMES_AND_ALIASES, upload_subs)


def make_upload_policy(names, upload_subs: _SubParsersAction[ArgumentParser]):
    upload_policy = upload_subs.add_parser(
        **name_and_aliases(names), formatter_class=fmt
    )
    upload_policy.add_argument(
        "-u", "--uid", help="uid of a previously-uploaded policy to update"
    )
    add_policy_file_arg(upload_policy)
