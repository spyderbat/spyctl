import spyctl.cli as cli
import spyctl.spyctl_lib as lib
import spyctl.resources.suppression_policies as sp
import spyctl.search as search
import spyctl.commands.apply as apply


def handle_suppress_trace_by_id(orig_id: str, include_users: bool):
    id = orig_id
    trace = search.search_for_trace_by_uid(id)
    if not trace:
        exit(1)
    summary_uid = trace.get(lib.TRACE_SUMMARY_FIELD)
    if not summary_uid:
        cli.err_exit(f"Unable to find a Trace Summary for Trace {id}")
    t_sum = search.search_for_trace_summary_by_uid(summary_uid)
    if not t_sum:
        exit(1)
    pol = sp.build_trace_suppression_policy(t_sum, include_users)
    cli.try_log("")
    if not prompt_upload_policy(pol):
        cli.try_log("Operation cancelled.")
        return
    apply.handle_apply_suppression_policy(pol.as_dict())


def prompt_upload_policy(pol: sp.TraceSuppressionPolicy) -> bool:
    query = "Scope:\n-------------\n"
    query += pol.policy_scope_string
    query += "\nSuppress spydertraces within this scope?"
    return cli.query_yes_no(query)
