import spyctl.cli as cli
import spyctl.spyctl_lib as lib
import spyctl.resources.baselines as b
import spyctl.resources.policies as p
import spyctl.resources.suppression_policies as sp
import spyctl.search as search
from typing import Optional


def handle_create_baseline(filename: str, output: str, name: str):
    resrc_data = lib.load_resource_file(filename)
    baseline = b.create_baseline(resrc_data, name)
    if output == lib.OUTPUT_DEFAULT:
        output = lib.OUTPUT_YAML
    cli.show(baseline, output)


def handle_create_guardian_policy(filename: str, output: str, name: str):
    resrc_data = lib.load_resource_file(filename)
    policy = p.create_policy(resrc_data, name)
    if output == lib.OUTPUT_DEFAULT:
        output = lib.OUTPUT_YAML
    cli.show(policy, output)


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
    if id:
        trace = search.search_for_trace_by_uid(id)
        if not trace:
            exit(1)
        summary_uid = trace.get(lib.TRACE_SUMMARY_FIELD)
        if not summary_uid:
            cli.err_exit(f"Unable to find a Trace Summary for Trace {id}")
        t_sum = search.search_for_trace_summary_by_uid(summary_uid)
        if not t_sum:
            exit(1)
        pol = sp.build_trace_suppression_policy(
            t_sum, include_users, name=name, **selectors
        )
    else:
        pol = sp.build_trace_suppression_policy(name=name, **selectors)
    if output == lib.OUTPUT_DEFAULT:
        output = lib.OUTPUT_YAML
    cli.show(pol.as_dict(), output)


def handle_create_flag_suppression_policy(
    id, include_users, output, **selectors
):
    pass
