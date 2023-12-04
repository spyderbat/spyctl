import time
from typing import Dict, List, Tuple

from tabulate import tabulate

import spyctl.cli as cli
import spyctl.resources.api_filters as _af
import spyctl.spyctl_lib as lib
import spyctl.api as api
import spyctl.config.configs as cfg


def agent_summary_output(agents: List[Dict]) -> str:
    header = ["NAME", "ID", "HEALTH", "ACTIVE BATS", "AGENT_VERSION"]
    data = []
    for agent in agents:
        data.append(agent_summary_data(agent))
    data.sort(key=lambda line: (calc_health_priority(line[2]), line[0]))
    return tabulate(data, header, tablefmt="plain")


def agent_summary_data(agent: Dict) -> List:
    active_bats = calc_active_bats(agent)
    rv = [
        agent["hostname"],
        agent["id"],
        agent["status"],
        active_bats,
        agent["agent_version"],
    ]
    return rv


def agents_output_wide(
    agents: List[Dict],
    source_data: Dict[str, Dict],
    include_latest_metrics: bool,
) -> None:
    header = [
        "NAME",
        "ID",
        "HEALTH",
        "ACTIVE BATS",
        "AGENT VERSION",
        "CLUSTER",
        "LAST DATA",
        "CLOUD REGION",
        "CLOUD TYPE",
    ]
    data = []
    if include_latest_metrics:
        header.extend(
            [
                "BANDWIDTH_1_MIN",
                "MEM_1_MIN",
                "CPU_1_MIN",
                "LATEST_METRICS_TIME",
            ]
        )
        latest_metrics = retrieve_latest_metrics(agents)
    else:
        latest_metrics = None
    for agent in agents:
        data.append(agent_output_wide_data(agent, source_data, latest_metrics))
    data.sort(key=lambda line: (calc_health_priority(line[2]), line[0]))
    print(tabulate(data, header, tablefmt="plain"))


def agent_output_wide_data(
    agent: Dict, source_data: Dict[str, Dict], latest_metrics: Dict = None
) -> List:
    active_bats = calc_active_bats(agent)
    rv = [
        agent["hostname"],
        agent["id"],
        agent["status"],
        active_bats,
        agent["agent_version"],
        agent.get("cluster_name") or lib.NOT_AVAILABLE,
    ]
    muid = agent["muid"]
    source = source_data.get(muid)
    if source:
        rv.extend(
            [
                source["last_data"],
                source["cloud_region"],
                source["cloud_type"],
            ]
        )
    else:
        rv.extend([lib.NOT_AVAILABLE, lib.NOT_AVAILABLE, lib.NOT_AVAILABLE])
    if latest_metrics:
        rv.extend(latest_metrics[agent["id"]])
    return rv


def calc_active_bats(agent: Dict):
    bat_statuses = agent.get(lib.AGENT_BAT_STATUSES, {})
    total = len(bat_statuses)
    active = 0
    for status in bat_statuses.values():
        if status.get("running", False) is True:
            active += 1
    return f"{active}/{total}"


def calc_health_priority(status):
    return lib.HEALTH_PRIORITY.get(status, 0)


VALID_METRICS_STATUSES = {
    lib.AGENT_HEALTH_CRIT,
    lib.AGENT_HEALTH_ERR,
    lib.AGENT_HEALTH_WARN,
    lib.AGENT_HEALTH_NORM,
}

LATEST_METRICS_NOT_AVAILABLE = (
    lib.NOT_AVAILABLE,
    lib.NOT_AVAILABLE,
    lib.NOT_AVAILABLE,
    lib.NOT_AVAILABLE,
)


def retrieve_latest_metrics(agents: List[Dict]) -> Dict[str, Tuple]:
    ctx = cfg.get_current_context()
    cli.try_log("Retrieving latest metrics for each agent.")
    rv = {}  # agent_uid -> tuple of latest metrics
    args = []
    pipeline = _af.AgentMetrics.generate_pipeline()
    # Build st, et for each agent
    latest_metrics_records = {}
    for agent in agents:
        # Default value is metrics not available
        rv[agent["id"]] = LATEST_METRICS_NOT_AVAILABLE
        if agent["status"] not in VALID_METRICS_STATUSES:
            continue
        source = agent["muid"]
        st = agent["time"] - 60
        et = max(time.time(), st + 120)
        t_blocks = api.time_blocks((st, et), api.MAX_TIME_RANGE_SECS)
        args.extend([(source, t_block) for t_block in t_blocks])
    agents_map = metrics_ref_map(agents)
    # Retrieve the latest metrics record for each agent
    for metrics_record in api.get_latest_agent_metrics(
        *ctx.get_api_data(), args, pipeline
    ):
        ref = metrics_record["ref"]
        if ref not in latest_metrics_records:
            latest_metrics_records[ref] = metrics_record
        else:
            old_time = latest_metrics_records[ref]["time"]
            new_time = metrics_record["time"]
            if new_time > old_time:
                latest_metrics_records[ref] = metrics_record
    # Build the metrics fields for output
    for ref_uid, metric_record in latest_metrics_records.items():
        agent = agents_map.get(ref_uid)
        if agent:
            agent_id = agent["id"]
            rv[agent_id] = __calc_latest_metrics(agent, metric_record)
    return rv


def __calc_latest_metrics(agent: Dict, metrics_record: Dict):
    kBps = str(round(metrics_record["bandwidth_1min_Bps"] / 1000, 1)) + "-kBps"
    total_mem = agent["total_mem_B"]
    mem_p = (
        str(
            round((metrics_record["mem_1min_B"]["agent"] / total_mem * 100), 2)
        )
        + "%"
    )
    cpu_p = str(round(metrics_record["cpu_1min_P"]["agent"] * 100, 2)) + "%"
    return (kBps, mem_p, cpu_p, lib.epoch_to_zulu(metrics_record["time"]))


def metrics_ref_map(agents: List[Dict]) -> Dict[str, Dict]:
    rv = {}
    for agent in agents:
        ref_string = f"{agent['id']}"
        rv[ref_string] = agent
    return rv


def metrics_header() -> str:
    columns = [
        "AGENT_NAME",
        "AGENT ID",
        "BANDWIDTH BYTES PER SECOND (AVG 1 MINUTE)",
        "CPU USAGE (% OF TIME UTILIZED 1 MINUTE on SCALE 0 to 1)",
        "MEMORY USAGE BYTES (AVG 1 MINUTE)",
        "CPU CORES",
        "TOTAL MEMORY BYTES",
        "TIME",
    ]
    return ",".join(columns) + "\n"


def usage_line(metrics_record: Dict, agent_record: Dict) -> str:
    data = [
        agent_record["hostname"],
        agent_record["id"],
        str(metrics_record["bandwidth_1min_Bps"]),
        str(metrics_record["cpu_1min_P"]["agent"]),
        str(metrics_record["mem_1min_B"]["agent"]),
        str(agent_record["num_cores"]),
        str(agent_record.get("total_mem_B", "N/A")),
        str(metrics_record["time"]),
    ]
    return ",".join(data) + "\n"


def usage_dict(metrics_record: Dict, agent_record: Dict) -> str:
    rv = {
        "agent_name": agent_record["hostname"],
        "agent_id": agent_record["id"],
        "bandwidth_1min_Bps": metrics_record["bandwidth_1min_Bps"],
        "cpu_usage_1min": metrics_record["cpu_1min_P"]["agent"],
        "mem_usage_B": metrics_record["mem_1min_B"]["agent"],
        "cpu_cores": agent_record["num_cores"],
        "total_mem_B": agent_record.get("total_mem_B", "N/A"),
        "time": metrics_record["time"],
    }
    return rv
