import spyctl.api as api
import spyctl.config.configs as cfg
import spyctl.cli as cli
from typing import Optional, Dict
import spyctl.spyctl_lib as lib
import json


def search_for_trace_by_uid(
    uid: str, ctx: cfg.Context = None
) -> Optional[Dict]:
    if not uid.startswith("trace:"):
        cli.err_exit("Expected uid in search for trace to start with 'trace:'")
    cli.try_log("Searching for trace object...")
    schema = lib.MODEL_SPYDERTRACE_PREFIX
    datatype = lib.DATATYPE_SPYDERGRAPH
    return search_for_obj_by_uid(uid, schema, datatype, ctx)


def search_for_trace_summary_by_uid(
    uid: str, ctx: cfg.Context = None
) -> Optional[Dict]:
    if not uid.startswith("fprint:trace"):
        cli.err_exit(
            "Expected uid in search for trace to start with 'fprint:trace'"
        )
    cli.try_log("Searching for trace summary...")
    schema = lib.MODEL_FINGERPRINT_PREFIX
    datatype = lib.DATATYPE_FINGERPRINTS
    return search_for_obj_by_uid(uid, schema, datatype, ctx)


def search_for_obj_by_uid(
    uid: str, schema: str, datatype: str, ctx: cfg.Context = None
) -> Optional[Dict]:
    if not ctx:
        ctx = cfg.get_current_context()
    resp = api.get_object_by_id(
        *ctx.get_api_data(),
        id=uid,
        schema=schema,
        datatype=datatype,
    )
    if resp.status_code != 200:
        cli.try_log(f"{resp.text}", is_warning=True)
        return None
    else:
        lines = resp.text.splitlines()
        if len(lines) < 2:
            cli.try_log(
                f"Unable to find {schema} object with id {uid}",
                is_warning=True,
            )
            return None
        try:
            obj: Dict = json.loads(lines[1])
        except json.JSONDecodeError:
            cli.try_log(
                "Unable to parse json returned by the spyderbat API",
                is_warning=True,
            )
            return None
    return obj
