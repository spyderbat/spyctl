#!/usr/bin/env python3


"""
    This program prints a CSV file with the statistics of CPU, memory, and
    bandwidth utilization across a fleet of agents. 

    Fetch the data using, for example,
         spyctl get agents --usage-json -t 24h > usage.json

    Generate the CSV using
         ./agent.py -i usage.json > usage.csv

"""

import json
import argparse
import sys
import gzip
import math
from collections import defaultdict
import traceback


# -------------------------------------------------------------
def _parse_cmd_line():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-i", "--infile", required=True)
    args = parser.parse_args()
    return args


# -------------------------------------------------------------

options = _parse_cmd_line()

# Read the infile and print if it's one we're looking for
if options.infile.endswith("gz"):
    infile = gzip.open(options.infile, "rt")
else:
    infile = open(options.infile, "r")


def percentile(data, q):
    try:
        data_sorted = sorted(data)
        index = math.ceil(q / 100 * len(data_sorted))
        if index >= len(data):
            index = len(data) - 1
        return data_sorted[index]
    except IndexError:
        breakpoint()


agent = {}
mem = defaultdict(list)
cpu = defaultdict(list)
bandwidth = defaultdict(list)
try:
    for line in infile:
        rec = json.loads(line)
        agent_id = rec["agent_id"]
        agent[agent_id] = rec
        mem[agent_id].append(rec["mem_usage_B"])
        cpu[agent_id].append(rec["cpu_usage_1min"])
        bandwidth[agent_id].append(rec["bandwidth_1min_Bps"])
except Exception as exc:
    traceback.print_exc()
    print(exc)
infile.close()

print(f"agent,cpu mean,cpu p90,cpu p99,cpu max,mem mean,mem p90,mem p99,mem max,bps mean,bps p90,bps p99,bps max")
for agent_id in cpu:
    name = agent[agent_id]["agent_name"]
    w = [name]
    for label, table in [
        ("CPU", cpu),
        ("Mem", mem),
        ("Bps", bandwidth),
    ]:
        data = table[agent_id]
        mean = sum(data) / len(data)
        p90 = percentile(data, 90)
        p99 = percentile(data, 99)
        largest = max(data)
        w.extend([repr(mean), repr(p90), repr(p99), repr(largest)])
    print(','.join(w))
