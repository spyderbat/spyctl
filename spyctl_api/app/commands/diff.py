from dataclasses import dataclass

from spyctl.commands.merge import merge_resource

import app.app_lib as app_lib
import app.exceptions as ex
from typing import Dict, List

# ------------------------------------------------------------------------------
# Diff Object with Object(s)
# ------------------------------------------------------------------------------


@dataclass
class DiffInput:
    object: Dict
    diff_objects: List[Dict]
    org_uid: str = ""
    api_key: str = ""
    api_url: str = ""


@dataclass
class DiffOutput:
    diff_data: str


def diff(i: DiffInput) -> DiffOutput:
    spyctl_ctx = app_lib.generate_spyctl_context(
        i.org_uid, i.api_key, i.api_url
    )
    merge_data = merge_resource(
        i.object,
        "API Diff Request Object",
        i.diff_objects,
        ctx=spyctl_ctx,
    )
    if not merge_data:
        msg = app_lib.flush_spyctl_log_messages()
        ex.internal_server_error(msg)
    app_lib.flush_spyctl_log_messages()
    return DiffOutput(merge_data.get_diff())
