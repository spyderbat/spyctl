from __future__ import annotations
from argparse import *
from argparse import _SubParsersAction
import sys
import time

from traitlets import default


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


def minutes_back(time_str):
    if int(time_str) < 0:
        raise ValueError("time must be in the past")
    return time.time() - int(time_str) * 60


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

def add_time_arg(parser):
    parser.add_argument('-t', '--time', help="minutes back from now to collect data from", type=minutes_back, default="0")


def parse_args():
    desc = "a tool to help manage Spyderbat fingerprints and policies"
    epilog = "object inputs can be given as file names, text, or piped\n" \
        "ex: prints get fingerprints --pods file_with_pods.txt\n" \
        "    prints get fingerprints --pods my-pod-fsd23\n" \
        "    prints get pods --namespace default | prints get fingerprints --pods"
    parser = ArgumentParser(description=desc, epilog=epilog, formatter_class=fmt)
    parser.add_argument('-v', '--no-validation', action='store_true', help="disables validation, reducing API calls. disallows object names as inputs")
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
    selector_group = get_fingerprint.add_mutually_exclusive_group(required=True)
    selector_group.add_argument('-c', '--clusters', nargs='?', const='-')
    selector_group.add_argument('-m', '--machines', nargs='?', const='-')
    selector_group.add_argument('-p', '--pods', nargs='?', const='-')
    get_fingerprint.add_argument('-t', '--time', help="minutes back from now to collect fingerprints from after", type=minutes_back, required=True)
    get_fingerprint.add_argument('--end-time', help="minutes back from now to stop collecting fingerprints (default=0)", type=minutes_back, default="0")
    add_output_arg(get_fingerprint)

def make_get_policy(get_subs: _SubParsersAction[ArgumentParser]):
    names = ['policies', 'pol', 'pols', 'policy']
    get_policy = get_subs.add_parser(**name_and_aliases(names), formatter_class=fmt)
    get_policy.add_argument('type', choices=['container', 'service'], help="the type of policies to get")
    selector_group = get_policy.add_mutually_exclusive_group(required=True)
    selector_group.add_argument('-c', '--clusters', nargs='?', const='-')
    selector_group.add_argument('-m', '--machines', nargs='?', const='-')
    selector_group.add_argument('-p', '--pods', nargs='?', const='-')
    get_policy.add_argument('-t', '--time', help="minutes back from now to collect policies from after", type=minutes_back, required=True)
    get_policy.add_argument('--end-time', help="minutes back from now to stop collecting policies (default=0)", type=minutes_back, default="0")
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
    