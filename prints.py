from genericpath import exists
from args import parse_args, get_names
from cli import *
from diff import show_fingerprint_diff
from fingerprints import fingerprint_input
from get import *
from merge import merge_fingerprints


def main():
    args = parse_args()
    cmd = args.subcommand
    if cmd in get_names("configure"):
        handle_configure(args)
    elif cmd in get_names("get"):
        handle_get(args)
    elif cmd in get_names("compare"):
        handle_compare(args)
    elif cmd in get_names("merge"):
        handle_merge(args)
    elif cmd in get_names("policy"):
        handle_policy(args)


def handle_configure(args):
    doc = {}
    if exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            doc = yaml.load(f, yaml.Loader)
            if doc is None:
                doc = {}
    if args.deployment:
        doc["deployment"] = args.deployment
    deployment = doc.get("deployment", "default")
    sub = doc.get(deployment, {})
    if args.api_key:
        sub["api_key"] = args.api_key
    if args.api_url:
        sub["api_url"] = args.api_url
    if args.org:
        if not sub.get("api_key") or not sub.get("api_url"):
            err_exit("cannot set organization without API key and url")
        orgs = get_orgs(sub["api_url"], sub["api_key"], api_err_exit)
        found = False
        for uid, name in zip(*orgs):
            if args.org == name or args.org == uid:
                if name == "Defend The Flag":
                    err_exit("invalid organization")
                sub["org_uid"] = uid
                found = True
                break
        if not found:
            err_exit("organization did not exist in specified API key and url")
    doc[deployment] = sub
    with open(CONFIG_PATH, 'w') as f:
        yaml.dump(doc, f)


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
    elif tgt in get_names("policies"):
        handle_get_policies(args)


def handle_compare(args):
    fingerprints = fingerprint_input(args)
    fingerprints = [f.get_output() for f in fingerprints]
    show_fingerprint_diff(fingerprints)


def handle_merge(args):
    fingerprints = fingerprint_input(args)
    fingerprints = [f.get_output() for f in fingerprints]
    merged = merge_fingerprints(fingerprints)
    show(merged, args.output)


def handle_policy(args):
    sub = args.policy_subcommand
    if sub == "template":
        handle_policy_template(args)

def handle_policy_template(args):
    pass


if __name__ == "__main__":
    main()
