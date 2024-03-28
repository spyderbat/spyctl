#!/usr/bin/env python3

import math
from collections import defaultdict
import traceback


def percentile(data, q):
    try:
        data_sorted = sorted(data)
        index = math.ceil(q / 100 * len(data_sorted))
        if index >= len(data):
            index = len(data) - 1
        return data_sorted[index]
    except IndexError:
        breakpoint()


def compute_stats(metrics: list) -> dict:
    if not metrics:
        return {}
    agent = {}
    mem = defaultdict(list)
    cpu = defaultdict(list)
    bandwidth = defaultdict(list)
    try:
        for rec in metrics:
            agent_id = rec["ref"]
            agent[agent_id] = rec
            mem[agent_id].append(rec["mem_1min_B"]["agent"])
            cpu[agent_id].append(rec["cpu_1min_P"]["agent"])
            bandwidth[agent_id].append(rec["bandwidth_1min_Bps"])
            mem["all_agents"].append(rec["mem_1min_B"]["agent"])
            cpu["all_agents"].append(rec["cpu_1min_P"]["agent"])
            bandwidth["all_agents"].append(rec["bandwidth_1min_Bps"])
    except Exception as exc:
        breakpoint()
        traceback.print_exc()
        print(exc)

    rv = {}
    for agent_id in cpu:
        if agent_id == "all_agents":
            continue
        rv[agent_id] = {}
        name = agent[agent_id]["hostname"]
        rv[agent_id]["name"] = name
        w = [name]
        for label, table in [
            ("cpu", cpu),
            ("mem", mem),
            ("bps", bandwidth),
        ]:
            rv[agent_id].setdefault(label, {})
            data = table[agent_id]
            mean = sum(data) / len(data)
            rv[agent_id][label]["mean"] = mean
            p90 = percentile(data, 90)
            rv[agent_id][label]["p90"] = p90
            p99 = percentile(data, 99)
            rv[agent_id][label]["p99"] = p99
            largest = max(data)
            rv[agent_id][label]["max"] = largest
            w.extend([repr(mean), repr(p90), repr(p99), repr(largest)])

    summary = {}
    for label, table in [
        ("cpu", cpu),
        ("mem", mem),
        ("bps", bandwidth),
    ]:
        summary.setdefault(label, {})
        data = table["all_agents"]
        mean = sum(data) / len(data)
        summary[label]["mean"] = mean
        p90 = percentile(data, 90)
        summary[label]["p90"] = p90
        p99 = percentile(data, 99)
        summary[label]["p99"] = p99
        largest = max(data)
        summary[label]["max"] = largest
        w.extend([repr(mean), repr(p90), repr(p99), repr(largest)])
    return {
        "agents": rv,
        "summary": summary
    }