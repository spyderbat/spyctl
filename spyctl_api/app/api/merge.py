import json

import spyctl.commands.validate as val
import spyctl.schemas as schemas
import spyctl.spyctl_lib as lib
from fastapi import APIRouter
from pydantic import BaseModel, Field, validator

import app.app_lib as app_lib
import app.commands.merge as cmd_merge
import app.exceptions as ex

router = APIRouter(prefix="/api/v1")


# ------------------------------------------------------------------------------
# Merge Object(s) into Object
# ------------------------------------------------------------------------------


class MergeHandlerInput(BaseModel):
    object: str = Field(title="The primary object of the merge")
    merge_objects: str = Field(
        title="The object(s) to merge into the primary object."
    )
    org_uid: str
    api_key: str
    api_url: str

    @validator("object")
    def object_must_be_valid_json_dict(cls, v):
        try:
            obj = json.loads(v)
            if not isinstance(obj, dict):
                ex.bad_request(
                    "The 'object' field does not contain a json dict"
                )
            if lib.KIND_FIELD not in obj:
                ex.bad_request(
                    f"The dictionary in obj must have a '{lib.KIND_FIELD}'"
                )
            if not schemas.valid_object(obj):
                messages = app_lib.flush_spyctl_log_messages()
                ex.bad_request(f"'object' failed validation.\n{messages}")
        except json.JSONDecodeError:
            ex.bad_request("Error decoding json for 'object' field.")
        app_lib.flush_spyctl_log_messages()
        return v

    @validator("merge_objects")
    def merge_objects_must_be_valid_json_list(cls, v):
        try:
            objs = json.loads(v)
            if not isinstance(objs, list) and not isinstance(objs, dict):
                ex.bad_request(
                    "The 'merge_objects' field does not contain a json list or"
                    " json dict"
                )
            if isinstance(objs, list):
                if not val.validate_list(objs):
                    messages = app_lib.flush_spyctl_log_messages()
                    ex.bad_request(
                        f"'merge_objects' failed validation.\n{messages}"
                    )
            else:
                if not val.validate_object(objs):
                    messages = app_lib.flush_spyctl_log_messages()
                    ex.bad_request(
                        f"'merge_objects' failed validation.\n{messages}"
                    )
        except json.JSONDecodeError:
            messages = app_lib.flush_spyctl_log_messages()
            ex.bad_request("Error decoding json for 'merge_objects' field.")
        app_lib.flush_spyctl_log_messages()
        return v


class MergeHandlerOutput(BaseModel):
    merged_object: str


@router.post("/merge")
def merge(
    i: MergeHandlerInput,
) -> MergeHandlerOutput:
    cmd_input = cmd_merge.MergeInput(
        i.object,
        i.merge_objects,
        i.org_uid,
        i.api_key,
        i.api_url,
    )
    output = cmd_merge.merge(cmd_input)
    return MergeHandlerOutput(merged_object=output.merged_object)
