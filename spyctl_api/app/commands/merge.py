import json
from dataclasses import dataclass

from spyctl.commands.merge import merge_resource

import app.app_lib as app_lib
import app.exceptions as ex

# ------------------------------------------------------------------------------
# Merge Object(s) into Object
# ------------------------------------------------------------------------------


@dataclass
class MergeInput:
    object: str
    merge_objects: str
    org_uid: str = ""
    api_key: str = ""
    api_url: str = ""


@dataclass
class MergeOutput:
    merged_object: str


def merge(i: MergeInput) -> MergeOutput:
    spyctl_ctx = app_lib.generate_spyctl_context(
        i.org_uid, i.api_key, i.api_url
    )
    try:
        object = json.loads(i.object)
        merge_objects = json.loads(i.merge_objects)
        merged_object = merge_resource(
            object, "API Merge Request Object", merge_objects, ctx=spyctl_ctx
        )
        if not merged_object:
            print(app_lib.flush_spyctl_log_messages())
            ex.internal_server_error()
        return MergeOutput(json.dumps(merged_object.get_obj_data()))
    except Exception:
        ex.internal_server_error()
