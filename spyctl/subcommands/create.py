import json
from typing import List

import yaml

import spyctl.cli as cli
import spyctl.spyctl_lib as lib
from spyctl.resources.fingerprints import Fingerprint
import spyctl.resources.baselines as b
from spyctl.resources.policies import Policy
from spyctl.subcommands.merge import MergeDumper


def handle_create_baseline(filename, output):
    try:
        with open(filename) as f:
            resrc_data = yaml.load(f, yaml.Loader)
    except Exception:
        try:
            resrc_data = json.load(filename)
        except Exception:
            cli.err_exit("Unable to load resource file.")
    if not isinstance(resrc_data, dict):
        cli.err_exit("Resource file does not contain a dictionary.")
    baseline = b.create_baseline(resrc_data)
    cli.show(baseline, output)


# def handle_create_policy(args, fingerprints: List[Fingerprint] = None):
#     # Builds a spyderbat policy from input or creates a default template
#     if fingerprints is not None and len(fingerprints) > 0:
#         if len(fingerprints) > 1:
#             fingerprints = [f.get_output() for f in fingerprints]
#             fingerprint = merge_fingerprints(fingerprints)
#             fingerprint = yaml.load(
#                 yaml.dump(fingerprint, Dumper=MergeDumper, sort_keys=False),
#                 yaml.Loader,
#             )
#         else:
#             fingerprint = fingerprints[0].get_output()
#         policy = Policy(args.type, fingerprint)
#     else:
#         policy = Policy(args.type)
#     show(policy.get_output(), args)
