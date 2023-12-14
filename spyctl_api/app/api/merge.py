import json
from typing import List, Union

import spyctl.schemas_v2 as schemas
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field, Json
from typing_extensions import Annotated

import app.app_lib as app_lib
import app.commands.merge as cmd_merge

router = APIRouter(prefix="/api/v1")

PrimaryObject = Annotated[
    Union[schemas.GuardianBaselineModel, schemas.GuardianPolicyModel],
    Field(discriminator="kind"),
]

MergeObject = Annotated[
    Union[
        schemas.GuardianBaselineModel,
        schemas.GuardianDeviationModel,
        schemas.GuardianFingerprintGroupModel,
        schemas.GuardianFingerprintModel,
        schemas.GuardianPolicyModel,
        schemas.UidListModel,
    ],
    Field(discriminator="kind"),
]

# ------------------------------------------------------------------------------
# Merge Object(s) into Object
# ------------------------------------------------------------------------------


class MergeHandlerInput(BaseModel):
    object: Json[PrimaryObject] = Field(
        title="The primary object of the merge"
    )
    merge_objects: Json[List[MergeObject]] = Field(
        title="The object(s) to merge into the primary object."
    )
    org_uid: str
    api_key: str
    api_url: str


class MergeHandlerOutput(BaseModel):
    merged_object: str


@router.post("/merge")
def merge(
    i: MergeHandlerInput,
    background_tasks: BackgroundTasks,
) -> MergeHandlerOutput:
    background_tasks.add_task(app_lib.flush_spyctl_log_messages)
    merge_objects = [
        json.loads(obj.json(by_alias=True, exclude_unset=True))
        for obj in i.merge_objects
    ]
    cmd_input = cmd_merge.MergeInput(
        json.loads(i.object.json(by_alias=True, exclude_unset=True)),
        merge_objects,
        i.org_uid,
        i.api_key,
        i.api_url,
    )
    output = cmd_merge.merge(cmd_input)
    return MergeHandlerOutput(merged_object=output.merged_object)
