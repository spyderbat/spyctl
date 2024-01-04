import json
from typing import Dict, List, Literal, Optional, Union

import spyctl.schemas_v2 as schemas
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field, Json
from typing_extensions import Annotated

import app.app_lib as app_lib
import app.commands.diff as cmd_diff

router = APIRouter(prefix="/api/v1")

PrimaryObject = Annotated[
    Union[schemas.GuardianBaselineModel, schemas.GuardianPolicyModel],
    Field(discriminator="kind"),
]

DiffObject = Annotated[
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
# Diff Object(s) into Object
# ------------------------------------------------------------------------------


class DiffHandlerInput(BaseModel):
    object: Json[PrimaryObject] = Field(title="The primary object of the diff")
    diff_objects: Json[List[DiffObject]] = Field(
        title="The object(s) to diff with the primary object."
    )
    org_uid: str
    api_key: str
    api_url: str
    full_diff: Optional[bool] = False
    content_type: Optional[Literal["text", "json"]] = Field(
        default="string", title="The content type of the diff data"
    )
    include_irrelevant: Optional[bool] = False


class DiffHandlerOutput(BaseModel):
    diff_data: str
    irrelevant: Optional[Dict[str, List[str]]]


@router.post("/diff")
def diff(
    i: DiffHandlerInput, background_tasks: BackgroundTasks
) -> DiffHandlerOutput:
    background_tasks.add_task(app_lib.flush_spyctl_log_messages)
    diff_objects = [
        json.loads(obj.json(by_alias=True, exclude_unset=True))
        for obj in i.diff_objects
    ]
    cmd_input = cmd_diff.DiffInput(
        json.loads(i.object.json(by_alias=True, exclude_unset=True)),
        diff_objects,
        i.org_uid,
        i.api_key,
        i.api_url,
        i.full_diff,
        i.content_type,
        i.include_irrelevant,
    )
    output = cmd_diff.diff(cmd_input)
    return DiffHandlerOutput(
        diff_data=output.diff_data, irrelevant=output.irrelevant
    )
