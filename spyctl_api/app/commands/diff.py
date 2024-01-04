import json
from dataclasses import dataclass
from typing import Dict, List, Optional
import logging

from spyctl.commands.merge import merge_resource

import app.app_lib as app_lib
import app.exceptions as ex

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
    full_diff: bool = False
    content_type: str = "text"
    include_irrelevant: bool = False


@dataclass
class DiffOutput:
    diff_data: str
    irrelevant: Optional[Dict[str, List[str]]] = None


def diff(i: DiffInput) -> DiffOutput:
    print(f"debug diff -- include_irrelevant: {i.include_irrelevant}")
    spyctl_ctx = app_lib.generate_spyctl_context(
        i.org_uid, i.api_key, i.api_url
    )
    merge_data = merge_resource(
        i.object,
        "API Diff Request Object",
        i.diff_objects,
        ctx=spyctl_ctx,
        check_irrelevant=i.include_irrelevant,
    )
    if not merge_data:
        msg = app_lib.flush_spyctl_log_messages()
        ex.internal_server_error(msg)
    app_lib.flush_spyctl_log_messages()
    if i.content_type == "json":
        diff_obj = True
    else:
        diff_obj = False
    diff_data = merge_data.get_diff(i.full_diff, diff_obj)
    print(
        f"debug diff -- has irrelevant objects: {len(merge_data.get_irrelevant_objects()) > 0}",
    )
    irrelevant = None
    if i.include_irrelevant:
        irrelevant = merge_data.get_irrelevant_objects()
    if isinstance(diff_data, str):
        if i.content_type == "json":
            raise ValueError(
                "Diff of this object type does not support JSON output."
            )
        return DiffOutput(diff_data, irrelevant=irrelevant)
    return DiffOutput(json.dumps(diff_data), irrelevant=irrelevant)
