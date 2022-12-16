from __future__ import annotations

import sys
import time
import click
from datetime import datetime
from typing import Dict, List

import dateutil.parser as dateparser

# from spyctl.fingerprints import FPRINT_TYPE_CONT, FPRINT_TYPE_SVC
# from spyctl.spyctl_lib import *


def parse_args(args: List = None):
    """Main entry point for spyctl argument parsing

    Args:
        args (List, optional): Arguments to parse (used for testing).
            If none, will default to sys.argv[1:]
    """
    if args is None:
        args == sys.argv[1:]
    desc = "spyctl controls various Spyderbat features"
    epilog = (
        'Use "spyctl <command> --help" for more information about a given'
        " command"
    )
    parser = ArgumentParser(description=desc, epilog=epilog, f)
    parser.parse_args(args)


if __name__ == "__main__":
    parse_args()
