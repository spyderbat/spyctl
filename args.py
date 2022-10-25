from __future__ import annotations
from argparse import *
from argparse import _SubParsersAction
from datetime import datetime
import time
import dateutil.parser as dateparser


class CustomHelpFormatter(RawDescriptionHelpFormatter):
    def _format_action_invocation(self, action):
        # changes "-p PODS, --pods PODS" tp "-p, --pods PODS"
        if action.option_strings:
            default = self._get_default_metavar_for_optional(action)
            args_string = self._format_args(action, default)
            return ', '.join(action.option_strings) + ' ' + args_string
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
            return ', '.join(choice_strs)
        else:
            return super()._format_action_invocation(action)
    
    def _format_args(self, action: Action, default_metavar: str) -> str:
        # changes "[files [files ...]]" to "[files ...]"
        if action.nargs == ZERO_OR_MORE:
            get_metavar = self._metavar_formatter(action, default_metavar)
            return '[%s ...]' % get_metavar(1)
        # changes "files [files ...]" to "files [...]"
        elif action.nargs == ONE_OR_MORE:
            get_metavar = self._metavar_formatter(action, default_metavar)
            return '%s [...]' % get_metavar(1)
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
            result = '{%s}' % ','.join(choice_strs)
            return lambda size: (result, ) * size
        return super()._metavar_formatter(action, default_metavar)

fmt = lambda prog: CustomHelpFormatter(prog)


def time_inp(time_str: str):
    past_seconds = 0
    try:
        try:
            past_seconds = int(time_str) * 60
        except ValueError:
            if time_str.endswith(('s', 'sc')):
                past_seconds = int(time_str[:-1])
            elif time_str.endswith(('m', 'mn')):
                past_seconds = int(time_str[:-1]) * 60
            elif time_str.endswith(('h', 'hr')):
                past_seconds = int(time_str[:-1]) * 60 * 60
            elif time_str.endswith(('d', 'dy')):
                past_seconds = int(time_str[:-1]) * 60 * 60 * 24
            elif time_str.endswith(('w', 'wk')):
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


def add_output_arg(parser):
    parser.add_argument('-o', '--output', choices=['json', 'yaml'], default='yaml')
    parser.add_argument('-f', '--filter', help="filter output objects by string")

def add_time_arg(parser):
    times = parser.add_mutually_exclusive_group()
    times.add_argument('-t', '--time', help="collect data at this time", type=time_inp)
    times.add_argument('-w', '--within', help="collect data from this time until now", metavar="TIME", type=time_inp)


def parse_args():
    desc = "a tool to help manage Spyderbat fingerprints and policies"
    epilog = "object inputs can be given as file names, text, or piped\n" \
        "ex: spyctl get fingerprints --pods file_with_pods.txt\n" \
        "    spyctl get fingerprints --pods my-pod-fsd23\n" \
        "    spyctl get pods --namespace default | spyctl get fingerprints --pods\n\n" \
        "time inputs are by default minutes back, but other formats can be specified\n" \
        "ex: -t 15: 15 minutes ago\n" \
        "    -t 2h: 2 hours ago\n" \
        "    -t 15:30: 3:30 PM today\n" \
        "    -t 01-01-2022: Jan 1. 2022 (12:00 AM)\n\n" \
        "as grep works poorly with multiline objects, outputs can be filtered with --filter\n" \
        "ex: -f \"kube\": matches any object with a value containing \"kube\"\n" \
        "    -f \"name=aws-*\": matches any object with a name field starting with \"aws-\""
    parser = ArgumentParser(description=desc, epilog=epilog, formatter_class=fmt)
    subs = parser.add_subparsers(title="subcommands", dest="subcommand", required=True)
    make_configure(subs)
    make_get(subs)
    make_compare(subs)
    make_merge(subs)
    make_policy(subs)
    return parser.parse_args()


def make_configure(subs: _SubParsersAction[ArgumentParser]):
    desc = "configure API information"
    names = ['configure', 'conf', 'config']
    configure = subs.add_parser(**name_and_aliases(names), description=desc, formatter_class=fmt)
    configure.add_argument('-d', '--deployment', help="the deployment to use and/or update")
    configure.add_argument('-k', '--api_key', metavar="KEY")
    configure.add_argument('-u', '--api_url', metavar="URL")
    configure.add_argument('-o', '--org', metavar="NAME_OR_UID")


def make_get(subs: _SubParsersAction[ArgumentParser]):
    desc = "get different types of information and objects"
    get = subs.add_parser('get', description=desc, formatter_class=fmt)
    get_subs = get.add_subparsers(title="targets", dest="get_target")
    make_get_cluster(get_subs)
    make_get_namespace(get_subs)
    make_get_machine(get_subs)
    make_get_pod(get_subs)
    make_get_fingerprint(get_subs)
    make_get_policy(get_subs)

def make_get_cluster(get_subs: _SubParsersAction[ArgumentParser]):
    names = ['clusters', 'clust', 'clusts', 'cluster']
    get_cluster = get_subs.add_parser(**name_and_aliases(names), formatter_class=fmt)
    add_time_arg(get_cluster)
    add_output_arg(get_cluster)

def make_get_namespace(get_subs: _SubParsersAction[ArgumentParser]):
    names = ['namespaces', 'name', 'names', 'namesp', 'namesps', 'namespace']
    get_namespace = get_subs.add_parser(**name_and_aliases(names), formatter_class=fmt)
    get_namespace.add_argument('-c', '--clusters', nargs='?', const='-', required=True)
    add_time_arg(get_namespace)
    add_output_arg(get_namespace)

def make_get_machine(get_subs: _SubParsersAction[ArgumentParser]):
    names = ['machines', 'mach', 'machs', 'machine']
    get_machine = get_subs.add_parser(**name_and_aliases(names), formatter_class=fmt)
    get_machine.add_argument('-c', '--clusters', nargs='?', const='-')
    add_time_arg(get_machine)
    add_output_arg(get_machine)

def make_get_pod(get_subs: _SubParsersAction[ArgumentParser]):
    names = ['pods', 'pod']
    get_pod = get_subs.add_parser(**name_and_aliases(names), formatter_class=fmt)
    get_pod.add_argument('-c', '--clusters', nargs='?', const='-')
    get_pod.add_argument('-m', '--machines', nargs='?', const='-')
    get_pod.add_argument('-n', '--namespaces', nargs='?', const='-')
    add_time_arg(get_pod)
    add_output_arg(get_pod)

def make_get_fingerprint(get_subs: _SubParsersAction[ArgumentParser]):
    names = ['fingerprints', 'print', 'prints', 'fingerprint']
    get_fingerprint = get_subs.add_parser(**name_and_aliases(names), formatter_class=fmt)
    get_fingerprint.add_argument('type', choices=['container', 'service'], help="the type of fingerprints to get")
    selector_group = get_fingerprint.add_mutually_exclusive_group()
    selector_group.add_argument('-c', '--clusters', nargs='?', const='-')
    selector_group.add_argument('-m', '--machines', nargs='?', const='-')
    selector_group.add_argument('-p', '--pods', nargs='?', const='-')
    add_time_arg(get_fingerprint)
    add_output_arg(get_fingerprint)

def make_get_policy(get_subs: _SubParsersAction[ArgumentParser]):
    names = ['policies', 'pol', 'pols', 'policy']
    get_policy = get_subs.add_parser(**name_and_aliases(names), formatter_class=fmt)
    get_policy.add_argument('type', choices=['container', 'service'], help="the type of policies to get")
    selector_group = get_policy.add_mutually_exclusive_group(required=True)
    selector_group.add_argument('-c', '--clusters', nargs='?', const='-')
    selector_group.add_argument('-m', '--machines', nargs='?', const='-')
    selector_group.add_argument('-p', '--pods', nargs='?', const='-')
    add_time_arg(get_policy)
    add_output_arg(get_policy)


def make_compare(subs: _SubParsersAction[ArgumentParser]):
    desc = "compare a set of fingerprints"
    names = ['compare', 'diff', 'comp']
    compare = subs.add_parser(**name_and_aliases(names), description=desc, formatter_class=fmt)
    compare.add_argument('files', help="fingerprint files to compare", type=FileType('r'), nargs='*')


def make_merge(subs: _SubParsersAction[ArgumentParser]):
    desc = "merge a set of fingerprints"
    names = ['merge', 'combine']
    merge = subs.add_parser(**name_and_aliases(names), description=desc, formatter_class=fmt)
    merge.add_argument('files', help="fingerprint files to merge", type=FileType('r'), nargs='*')
    add_output_arg(merge)


def make_policy(subs: _SubParsersAction[ArgumentParser]):
    desc = "manage policy objects"
    policy = subs.add_parser('policy', description=desc, formatter_class=fmt)
    policy_subs = policy.add_subparsers(title="subcommands", dest="policy_subcommand")
    make_policy_template(policy_subs)

def make_policy_template(policy_subs: _SubParsersAction[ArgumentParser]):
    desc = "template a policy from a set of fingerprints"
    template = policy_subs.add_parser('template', description=desc, formatter_class=fmt)
    template.add_argument('files', help="fingerprint files to template", type=FileType('r'), nargs='*')
    