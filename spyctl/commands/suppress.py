import spyctl.api as api
import spyctl.cli as cli
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
import json
from typing import Dict
import spyctl.resources.suppression_policies as s_pol


def handle_suppress_traces():
    pass
    # id = "fprint:trace:-BAeHadjTPM:ZGuxJQ:1964868:suspicious_command"
    # vf = time.time() - 86000
    # vt = time.time()
    # dt = "fingerprints"
    # rv = api.get_object_by_id(
    #     *cfg.get_current_context().get_api_data(),
    #     id,
    #     "model_fingerprint",
    #     (vf, vt),
    #     dt,
    # )
    # for line in rv.text.splitlines():
    #     print(json.dumps(line))


def handle_suppress_by_id(orig_id: str, include_users: bool):
    id = orig_id
    ctx = cfg.get_current_context()
    if id.startswith("fprint:trace"):
        cli.try_log("Searching for trace summary...")
        schema = lib.MODEL_FINGERPRINT_PREFIX
        datatype = lib.DATATYPE_FINGERPRINTS
    elif id.startswith("trace:"):
        cli.try_log("Searching for trace object...")
        schema = lib.MODEL_SPYDERTRACE_PREFIX
        datatype = lib.DATATYPE_SPYDERGRAPH
    else:
        cli.err_exit("Unrecognized ID format.")
    resp = api.get_object_by_id(
        *ctx.get_api_data(),
        id=id,
        schema=schema,
        datatype=datatype,
    )
    if resp.status_code != 200:
        cli.err_exit(f"{resp.text}")
    else:
        lines = resp.text.splitlines()
        if len(lines) < 2:
            cli.err_exit(f"Unable to find {schema} object with id {id}")
        obj: Dict = json.loads(lines[1])
        if schema == lib.MODEL_SPYDERTRACE_PREFIX:
            cli.try_log("Trace object found. Searching for trace summary...")
            id = obj.get("trace_summary")
            if not id:
                cli.err_exit(
                    f"Unable to find a Trace Summary for Trace {orig_id}"
                )
            schema = lib.MODEL_FINGERPRINT_PREFIX
            datatype = lib.DATATYPE_FINGERPRINTS
            resp = api.get_object_by_id(
                *ctx.get_api_data(),
                id=id,
                schema=schema,
                datatype=datatype,
            )
            if resp.status_code != 200:
                cli.err_exit(f"{resp.text}")
            else:
                lines = resp.text.splitlines()
                if len(lines) < 2:
                    cli.err_exit(
                        f"Unable to find {schema} object with id {id}"
                    )
                obj: Dict = json.loads(lines[1])
        cli.try_log("")
        pol = s_pol.create_suppression_policy(obj, include_users)
        if not prompt_upload_policy(pol):
            cli.try_log("Operation cancelled.")
        uid, pol_data = s_pol.get_data_for_api_call(pol)
        if uid:
            resp = api.put_policy_update(
                *ctx.get_api_data(), pol_uid=uid, data=pol_data
            )
            if resp.status_code == 200:
                cli.try_log(f"Successfully updated policy {uid}")
        else:
            resp = api.post_new_policy(*ctx.get_api_data(), data=pol_data)
            if resp.status_code == 200 and resp.text:
                uid = json.loads(resp.text).get("uid", "")
                cli.try_log(f"Successfully applied new policy with uid: {uid}")


def prompt_upload_policy(pol: s_pol.SuppressionPolicy) -> bool:
    query = "Scope:\n-------------\n"
    query += pol.policy_scope_string
    query += "\nSuppress spydertraces within this scope?"
    return cli.query_yes_no(query)
