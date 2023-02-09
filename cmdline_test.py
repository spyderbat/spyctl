#! /home/brhaub/spyctl_demo/bin/python3

import os
import sys
from pathlib import Path

from click.testing import CliRunner

import spyctl.spyctl_main as spyctl_main


def main_test():
    runner = CliRunner()
    result = runner.invoke(spyctl_main.main, sys.argv[1:])
    print(result.output)


if __name__ == "__main__":
    main_test()
