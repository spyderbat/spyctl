from collections import defaultdict
from typing import Tuple
from spyctl import api
import spyctl.config.configs as cfg
import spyctl.resources.api_filters as _af
from collections import Counter, defaultdict
from typing import Sequence, Tuple, Optional
from datetime import datetime
from . import reporter

s_cluster = "model_k8s_cluster:"
s_node = "model_k8s_node"
s_replicaset = "model_k8s_replicaset"
s_daemonset = "model_k8s_daemonset"
s_deployment = "model_k8s_deployment"
s_pod = "model_k8s_pod"
s_service = "model_k8s_service"
s_endpoint = "model_k8s_endpoint"
s_statefulset = "model_k8s_statefulset"
s_job = "model_k8s_job"
s_cronjob = "model_k8s_cronjob"
s_container = "model_container"
s_namespace = "model_k8s_namespace"
s_opsflags = "event_opsflag"
# s_event_metrics = "event_metric:agent"

k8s_schemas = [s_cluster, s_node, s_replicaset, s_daemonset, s_deployment,
               s_pod, s_service, s_namespace]
report_schemas = [s_opsflags] + k8s_schemas

def make_index(rec_list: list, schemas: list[str]) -> Tuple[dict, dict]:
    index = dict()
    schema_index: dict = defaultdict(dict)
    for rec in rec_list:
        for schema in schemas:
            if schema in rec["schema"]:
                index[rec["id"]] = rec
                schema_index[schema][rec["id"]] = rec
    return index, schema_index

class Reporter(reporter.Reporter):
    def collector(
            self,
            args: dict[str, str|float|int|bool],
            org_uid: str,
            api_key: str,
            api_url: str) -> list:
        cluid = args["cluid"]
        sources = [f"{cluid}_base", f"{cluid}_poco", f"{cluid}_flags"]
        data = api.get_cluster_full(
            api_url, api_key, org_uid,
            sources,
            (int(args["st"]), int(args["et"])),
            pipeline=None,
            limit_mem=False,
            disable_pbar_on_first=True
        )

        return list(data)

    def processor(
            self,
            data: list,
            args: dict[str, str|float|int|bool],
            mock: dict={},
            format: Optional[str]="md") -> dict:
        if not data:
            return {
                "error": {
                    "message": "No data available"
                }
            }
        context = dict()
        index, schema_index = make_index(rec_list=data, schemas=report_schemas)

        # Cluster name and id
        cluster = list(schema_index[s_cluster].values())[0]
        context["cluster"] = {
            "name": cluster["name"],
            "cluid": cluster["id"],
            "node_count": len(schema_index.get(s_node, []))
        }

        # Reporting period
        context["st"] = datetime.fromtimestamp(
            int(args["st"])).strftime("%Y-%m-%d %H:%M:%S")
        context["et"] = datetime.fromtimestamp(
            int(args["et"])).strftime("%Y-%m-%d %H:%M:%S")

        # Cluster metrics
        context["cluster_metrics"] = get_cluster_metrics(index, schema_index, format)

        # Node summary and usage
        node_usage = get_node_usage(index, schema_index)
        context["node_summary"] = get_node_summary(node_usage, format)
        context["node_headroom"] = get_node_headroom(node_usage, format)

        # Agent health
        health = get_agent_health(index, schema_index, format)
        context["nano_agent"] = health["nano_agent"]
        context["cluster_monitor"] = health["cluster_monitor"]

        # Ops flags
        context["opsflags"] = get_opsflags(index, schema_index, format)
        context.update(mock)
        return context


def get_cluster_metrics(
        index: dict,
        schema_index: dict,
        format: str) -> list[dict]:
    metrics = [
        {
            "name": "Number of nodes",
            "value": len(schema_index.get(s_node, []))
        },
        {
            "name": "Number of namespaces",
            "value": len(schema_index[s_namespace])
        },
        {
            "name": "Number of pods",
            "value": len(schema_index[s_pod])
        },
        {
            "name": "Number of deployments",
            "value": len(schema_index[s_deployment])
        },
        {
            "name": "Number of daemonsets",
            "value": len(schema_index[s_daemonset])
        },
        {
            "name": "Number of services",
            "value": len(schema_index[s_service])
        },
    ]
    return metrics


def get_node_summary(node_usage: dict, format: str) -> dict | Sequence[dict]:
    summary = {}
    for prop in ["instance_type", "cores", "arch",
                 "osImage", "containerRuntime"]:
        summary[prop] = dict(Counter(
            [node[prop] for node in node_usage.values()]))

    if format == "md":
        friendly = {
            "instance_type": "Instance Type",
            "cores": "Nr of cores",
            "arch": "Hardware Arch",
            "osImage": "OS",
            "containerRuntime": "Container Runtime"
        }
        md_summary = []
        for prop in friendly.keys():
            for i, key in enumerate(summary[prop]):
                md_summary.append({
                    "name": friendly[prop] if i == 0 else "",
                    "value": key,
                    "prop_count": summary[prop][key]
                })
        return md_summary
    return summary


def get_node_headroom(node_usage: dict, format: str) -> dict | Sequence[dict]:
    pod_keys = ["name", "instance_type", "cores",
                "capacity_pods", "usage_pods", "headroom_pods"]
    cpu_keys = ["name", "instance_type", "cores",
                "capacity_cpu", "usage_cpu", "headroom_cpu"]
    memory_keys = ["name", "instance_type", "cores",
                   "capacity_memory", "usage_memory", "headroom_memory"]

    headroom_pods = [
        {key: node[key] for key in pod_keys} for node in node_usage.values()
        if node["headroom_pods"] < 0
    ]

    headroom_cpu = [
        {key: node[key] for key in cpu_keys} for node in node_usage.values()
        if node["headroom_cpu"] < 0
    ]

    headroom_memory = [
        {key: node[key] for key in memory_keys} for node in node_usage.values()
        if node["headroom_memory"] < 0
    ]

    return {
        "pods": headroom_pods,
        "cpu": headroom_cpu,
        "memory": headroom_memory
    }


def get_node_usage(index: dict, schema_index: dict) -> dict[str, dict]:
    index_schema = schema_index
    node_usage = defaultdict(dict)
    nodes = index_schema[s_node].values()
    pods = index_schema[s_pod].values()
    for node in nodes:

        node_usage[node["metadata"]["name"]] = {
            "name": node["metadata"]["name"],
            "arch": node["k8s_status"]["nodeInfo"]["architecture"],
            "osImage": node["k8s_status"]["nodeInfo"]["osImage"],
            "containerRuntime": node[
                "k8s_status"]["nodeInfo"]["containerRuntimeVersion"],
            "instance_type": node[
                "metadata"]["labels"].get(
                    "node.kubernetes.io/instance-type", "unknown"),
            "cores": int(node["k8s_status"]["capacity"]["cpu"]),
            "capacity_pods": int(node["k8s_status"]["capacity"]["pods"]),
            "usage_pods": 0,
            "headroom_pods": 0,
            "capacity_memory": convert_unit(node[
                "k8s_status"]["capacity"]["memory"]),
            "usage_memory": 0,
            "headroom_memory": 0,
            "capacity_cpu": convert_unit(node[
                "k8s_status"]["capacity"]["cpu"]),
            "usage_cpu": 0,
            "headroom_cpu": 0,
            "taints": node["spec"].get("taints", []),
            "control_plane": node["metadata"]["labels"].get(
                "node-role.kubernetes.io/controlplane", False),
        }

    for pod in pods:
        node_name = pod["spec"].get("nodeName")
        if node_name:
            node_usage[node_name]["usage_pods"] += 1
            for container in pod["spec"]["containers"]:
                if "resources" not in container:
                    continue
                if "requests" not in container["resources"]:
                    continue
                node_usage[node_name]["usage_memory"] += convert_unit(
                    container["resources"]["requests"].get("memory", 0))
                node_usage[node_name]["usage_cpu"] += convert_unit(
                    container["resources"]["requests"].get("cpu", 0))

    for node in node_usage.values():
        node["headroom_pods"] = node["capacity_pods"] - node["usage_pods"]
        node["headroom_memory"] = node["capacity_memory"] - node["usage_memory"]
        node["headroom_cpu"] = node["capacity_cpu"] - node["usage_cpu"]
    return node_usage


def convert_unit(amount: str) -> float:
    if type(amount) is int:
        return amount
    stripped = amount.strip()
    if stripped.endswith("Ki"):
        return int(stripped[:-2])*1024
    if stripped.endswith("Mi"):
        return int(stripped[:-2])*1024*1024
    if stripped.endswith("Gi"):
        return int(stripped[:-2])*1024*1024*1024
    if stripped.endswith("Ti"):
        return int(stripped[:-2])*1024*1024*1024*1024
    if stripped.endswith("Pi"):
        return int(stripped[:-2])*1024*1024*1024*1024*1024
    if stripped.endswith("Ei"):
        return int(stripped[:-2])*1024*1024*1024*1024*1024*1024
    if stripped.endswith("K"):
        return int(stripped[:-1])*1000
    if stripped.endswith("M"):
        return int(stripped[:-1])*1000*1000
    if stripped.endswith("G"):
        return int(stripped[:-1])*1000*1000*1000
    if stripped.endswith("T"):
        return int(stripped[:-1])*1000*1000*1000*1000
    if stripped.endswith("P"):
        return int(stripped[:-1])*1000*1000*1000*1000*1000
    if stripped.endswith("E"):
        return int(stripped[:-1])*1000*1000*1000*1000*1000*1000
    if stripped.endswith("m"):
        return int(stripped[:-1])/1000
    return int(stripped)


def get_cont_health(status: dict) -> dict:
    return {
        'container_id': status['containerID'].split("://")[-1] if 'containerID' in status else "not present",
        'ready': status.get('ready', False),
        'started': status.get('started', False)
    }


def get_pod_health(rec: dict) -> bool:
    status = rec['k8s_status']
    phase = status.get('phase')
    cont_status = status.get('containerStatuses', [])

    cont_health = [get_cont_health(status) for status in cont_status]
    healthy = (rec["status"] == "closed" or
               (phase == "Running" and all([ch['ready'] and ch['started']
                                            for ch in cont_health]))
               )
    return healthy


def to_tuple(d: dict) -> tuple:
    return tuple(sorted(d.items()))


def to_dict(t: tuple) -> dict:
    return dict(t)


def get_agent_health(
        index: dict,
        schema_index: dict,
        format: str) -> dict:

    rv = {"nano_agent": {},
          "cluster_monitor": {}}
    nodes = schema_index[s_node].values()
    nano_agent_ds = [ds for ds in schema_index[s_daemonset].values()
                     if "nanoagent" in ds["metadata"]["name"]]
    nano_agents = [pod for pod in schema_index[s_pod].values()
                   if "nanoagent" in pod["metadata"]["name"]]

    unhealthy_agents = [agent for agent in nano_agents
                        if not get_pod_health(agent)]

    nodes_missing_agents = [
        node for node in nodes
        if node["metadata"]["name"] not in
        [agent["spec"].get("nodeName") for agent in nano_agents]
    ]
    nano_healthy = len(unhealthy_agents) == 0 and len(nodes_missing_agents) == 0

    rv["nano_agent"]["healthy"] = nano_healthy
    rv["nano_agent"]["unhealthy_agents"] = [
        {
            "name": n["metadata"]["name"],
            "status": n["k8s_status"]["phase"],
            "node": n["spec"].get("nodeName", "not assigned to a node")
        } for n in unhealthy_agents
    ]
    rv["nano_agent"]["nodes_not_running"] = [
        {
            "name": n["metadata"]["name"],
            "taints": n["spec"].get("taints", [])
        } for n in nodes_missing_agents
    ]

    node_taints = set()
    for node in nodes:
        for taint in node["spec"].get("taints", []):
            node_taints.add(to_tuple(taint))
    nano_tolerations = set()
    for ds in nano_agent_ds:
        for taint in ds["spec"].get(
            "template", {}).get(
                "spec", {}).get("tolerations", []):
            nano_tolerations.add(to_tuple(taint))

    nano_missing_tolerations = [to_dict(taint)
                                for taint in node_taints - nano_tolerations]
    rv["nano_agent"]["missing_tolerations"] = nano_missing_tolerations

    cluster_monitor = [pod for pod in schema_index[s_pod].values()
                       if "clustermonitor" in pod["metadata"]["name"]]
    monitor_healthy = (
        len(cluster_monitor) == 1 and
        get_pod_health(cluster_monitor[0])
    )
    rv["cluster_monitor"]["healthy"] = monitor_healthy

    cluster_monitor_dep = [dep for dep in schema_index[s_deployment].values()
                           if "clustermonitor" in dep["metadata"]["name"]]
    cm_tolerations = set()
    for dep in cluster_monitor_dep:
        for taint in dep["spec"].get(
            "template", {}).get(
                "spec", {}).get("tolerations", []):
            cm_tolerations.add(to_tuple(taint))

    cm_missing_tolerations = [to_dict(taint)
                              for taint in node_taints - nano_tolerations]
    rv["cluster_monitor"]["missing_tolerations"] = cm_missing_tolerations
    return rv


def get_opsflags(index: dict, schema_index: dict, format: str) -> list:
    rv = []
    for flag in schema_index[s_opsflags].values():
        time_str = datetime.fromtimestamp(
            flag["time"]).strftime("%Y-%m-%d %H:%M:%S")
        rv.append({
                "time": time_str,
                "type": flag["schema"].split(":")[1],
                "description": flag["description"],
                "link": flag["linkback"]
            })
    return rv
