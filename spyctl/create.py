from typing import List

import yaml

from spyctl.cli import show
from spyctl.fingerprints import Fingerprint
from spyctl.merge import MergeDumper, merge_fingerprints
from spyctl.policies import Policy


def handle_create_policy(args, fingerprints: List[Fingerprint] = None):
    # Builds a spyderbat policy from input or creates a default template
    if fingerprints is not None and len(fingerprints) > 0:
        if len(fingerprints) > 1:
            fingerprints = [f.get_output() for f in fingerprints]
            fingerprint = merge_fingerprints(fingerprints)
            fingerprint = yaml.load(
                yaml.dump(fingerprint, Dumper=MergeDumper, sort_keys=False),
                yaml.Loader,
            )
        else:
            fingerprint = fingerprints[0].get_output()
        policy = Policy(args.type, fingerprint)
    else:
        policy = Policy(args.type)
    show(policy.get_output(), args)
