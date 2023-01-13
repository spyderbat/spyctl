#! /usr/bin/env python3

from spyctl.args import get_names, parse_args
from spyctl.cli import *
from spyctl.commands.create import handle_create_policy
from spyctl.commands.diff import show_fingerprint_diff
from spyctl.resources.fingerprints import InvalidFingerprintError
from spyctl.commands.get import *
from spyctl.commands.merge import MergeDumper, merge_fingerprints
from spyctl.resources.policies import PolicyTypeError
import spyctl.subcommands.manage as manage
import spyctl.config.configs as u_conf
import spyctl.subcommands.upload as upload
import spyctl.commands.delete as d


def main():
    args = parse_args()
    cmd = args.subcommand
    if args.selected_deployment:
        u_conf.set_selected_deployment(args.selected_deployment)
    if cmd in get_names("configure"):
        handle_configure(args)
    elif cmd in get_names("compare"):
        handle_compare(args)
    elif cmd in get_names("create"):
        handle_create(args)
    elif cmd in get_names("delete"):
        handle_delete(args)
    elif cmd in get_names("get"):
        handle_get(args)
    elif cmd in get_names("manage"):
        handle_manage(args)
    elif cmd in get_names("merge"):
        handle_merge(args)
    elif cmd in get_names("upload"):
        handle_upload(args)


def handle_configure(args):
    cmd = args.config_cmd
    if cmd == "add":
        u_conf.handle_config_add(args)
    elif cmd == "update":
        u_conf.handle_config_update(args)
    elif cmd == "default":
        u_conf.handle_config_setdefault(args)
    elif cmd == "delete":
        u_conf.handle_config_delete(args)
    elif cmd == "show":
        u_conf.handle_config_show(args)


def handle_get(args):
    tgt = args.get_target
    if tgt in get_names("clusters"):
        handle_get_clusters(args)
    if tgt in get_names("namespaces"):
        handle_get_namespaces(args)
    elif tgt in get_names("machines"):
        handle_get_machines(args)
    elif tgt in get_names("pods"):
        handle_get_pods(args)
    elif tgt in get_names("fingerprints"):
        handle_get_fingerprints(args)
    elif tgt in get_names("spyderbat-policy"):
        handle_get_policies(args)


def handle_compare(args):
    fingerprints = fingerprint_input(args.files)
    fingerprints = [f.get_output() for f in fingerprints]
    show_fingerprint_diff(fingerprints)


def handle_delete(args):
    cmd = args.delete_cmd
    if cmd in get_names("spyderbat-policy"):
        d.handle_delete_policy(args)


def handle_merge(args):
    fingerprints = fingerprint_input(args.files)
    fingerprints = [f.get_output() for f in fingerprints]
    merged = merge_fingerprints(fingerprints)
    merged = yaml.load(
        yaml.dump(merged, Dumper=MergeDumper, sort_keys=False), yaml.Loader
    )
    show(merged, args)


def handle_create(args):
    tgt = args.create_target
    if tgt in get_names("spyderbat-policy"):
        if args.fingerprints is not None:
            try:
                if args.fingerprints == "-":
                    files = []
                else:
                    files = [open(args.fingerprints)]
                fingerprints = fingerprint_input(files)
                handle_create_policy(args, fingerprints)
            except InvalidFingerprintError as e:
                try_log(" ".join(e.args))
            except PolicyTypeError as e:
                try_log(" ".join(e.args))
            finally:
                try:
                    files[0].close()
                except Exception:
                    pass
        else:
            handle_create_policy(args)


def handle_upload(args):
    cmd = args.upload_cmd
    if cmd in get_names("spyderbat-policy"):
        upload.handle_upload_policy(args)


def handle_manage(args):
    cmd = args.manage_cmd
    if cmd in get_names("spyderbat-policy"):
        manage.handle_manage_policy(args)


def handle_policy_template(args):
    pass


if __name__ == "__main__":
    main()
