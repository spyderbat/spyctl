from __future__ import annotations
import time
from datetime import datetime
from collections import defaultdict
from typing import Tuple, Optional
from spyctl import api
import spyctl.config.configs as cfg
import spyctl.resources.api_filters as _af
from . import agent_stats
from . import reporter

s_cluster = "model_k8s_cluster"
s_node = "model_k8s_node"
s_event_metrics = "event_metric:agent"

report_schemas = [s_cluster, s_node, s_event_metrics]

def make_index(rec_list: list, schemas: list[str]) -> Tuple[dict, dict]:
    index = dict()
    schema_index = defaultdict(dict)
    for rec in rec_list:
        for schema in schemas:
            if schema in rec["schema"]:
                index[rec["id"]] = rec
                schema_index[schema][rec["id"]] = rec
    return index, schema_index

class Reporter():
    def collector(
            self,
            args: dict[str, str|float|int|bool],
            org_uid: str,
            api_key: str,
            api_url: str) -> list:

        sources = [f"global:{org_uid}"]
        filters = {"cluster": args["cluster"]}
        pipeline = _af.Agents.generate_pipeline(
            None, None, True, filters=filters
        )
        st = int(args["st"])
        et = int(args["et"])
        agent_st = st_at_least_2hrs(st)
        agents = list(api.get_agents(
            api_url, api_key, org_uid,
            sources,
            time=(agent_st, et),
            pipeline=pipeline,
            limit_mem=False,
            disable_pbar_on_first=True
        ))

        sources = [agent["muid"] for agent in agents]
        pipeline = _af.AgentMetrics.generate_pipeline()
        metrics = api.get_agent_metrics(
            api_url, api_key, org_uid,
            sources,
            (agent_st, et),
            pipeline,
            limit_mem=False,
            disable_pbar_on_first=True
        )
        return agents + list(metrics)


    def processor(
            self,
            data: list,
            args: dict[str, str|float|int|bool],
            mock: dict={},
            format: Optional[str]="md") -> dict:
        context = {}
        index, schema_index = make_index(rec_list=data, schemas=report_schemas)


        # Cluster name
        context["cluster"] = {
            "name": args["cluster"],
        }

        st = int(args["st"])
        et = int(args["et"])

        # Reporting period
        context["st"] = datetime.fromtimestamp(st).strftime("%Y-%m-%d %H:%M:%S")
        context["et"] = datetime.fromtimestamp(et).strftime("%Y-%m-%d %H:%M:%S")

        # Filter event_metrics just to the ones for this cluster
        metrics = schema_index[s_event_metrics].values()

        # Compute stats
        stats = agent_stats.compute_stats(metrics)
        context["agent_metrics"] = stats["agents"]
        context["metrics_summary"] = stats["summary"]
        context.update(mock)
        return context


def st_at_least_2hrs(st: float):
    two_hours_secs = 60 * 60 * 2
    now = time.time()
    if now - st < two_hours_secs:
        return now - two_hours_secs
    return st