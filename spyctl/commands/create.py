import json
from typing import Dict, List, Optional

import spyctl.cli as cli
import spyctl.commands.validate as val
import spyctl.config.configs as cfg
import spyctl.resources.baselines as b
import spyctl.resources.policies as p
import spyctl.resources.suppression_policies as sp
import spyctl.search as search
import spyctl.spyctl_lib as lib


def handle_create_baseline(filename: str, output: str, name: str):
    resrc_data = lib.load_resource_file(filename)
    baseline = b.create_baseline(resrc_data, name)
    if output == lib.OUTPUT_DEFAULT:
        output = lib.OUTPUT_YAML
    cli.show(baseline, output)


def handle_create_guardian_policy(
    filename: str,
    output: str,
    name: str,
    ignore_procs: List,
    ignore_conns: List,
):
    policy = create_guardian_policy_from_file(
        filename, name, ignore_procs, ignore_conns
    )
    if output == lib.OUTPUT_DEFAULT:
        output = lib.OUTPUT_YAML
    cli.show(policy, output)


def create_guardian_policy_from_file(
    filename: str, name: str, ignore_procs: List = [], ignore_conns: List = []
):
    resrc_data = lib.load_resource_file(filename)
    policy = p.create_policy(resrc_data, name, ignore_procs, ignore_conns)
    return policy


def create_guardian_policy_from_json(
    name: str, input_objects: List[Dict], ctx: cfg.Context
):
    policy = p.create_policy(input_objects, name, ctx)
    return policy


def handle_create_suppression_policy(
    type: str,
    id: Optional[str],
    include_users: bool,
    output: str,
    name: str = None,
    **selectors,
):
    if type == lib.POL_TYPE_TRACE:
        handle_create_trace_suppression_policy(
            id, include_users, output, name, **selectors
        )


def handle_create_trace_suppression_policy(
    id, include_users, output, name: str = None, **selectors
):
    pol = create_trace_suppression_policy(id, include_users, name, **selectors)
    if output == lib.OUTPUT_DEFAULT:
        output = lib.OUTPUT_YAML
    cli.show(pol.as_dict(), output)


def create_trace_suppression_policy(
    id, include_users, name: str = None, ctx: cfg.Context = None, **selectors
) -> sp.TraceSuppressionPolicy:
    if id:
        trace = search.search_for_trace_by_uid(id, ctx)
        if not trace:
            exit(1)
        summary_uid = trace.get(lib.TRACE_SUMMARY_FIELD)
        if not summary_uid:
            cli.err_exit(f"Unable to find a Trace Summary for Trace {id}")
        t_sum = search.search_for_trace_summary_by_uid(summary_uid, ctx)
        if not t_sum:
            exit(1)
        pol = sp.build_trace_suppression_policy(
            t_sum, include_users, name=name, **selectors
        )
    else:
        pol = sp.build_trace_suppression_policy(name=name, **selectors)
    return pol


def handle_create_flag_suppression_policy(
    id, include_users, output, **selectors
):
    pass
