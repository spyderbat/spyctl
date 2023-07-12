from fastapi import APIRouter
from pydantic import BaseModel, Field, Json
from typing import Dict, List, Union, Literal, Optional
from typing_extensions import Annotated

import app.commands.create as cmd_create
import spyctl.schemas_v2 as schemas
import spyctl.spyctl_lib as lib

router = APIRouter(prefix="/api/v1")

# ------------------------------------------------------------------------------
# Create Suppression Policy
# ------------------------------------------------------------------------------


def undash(s: str) -> str:
    return s.replace("-", "_")


class CreateSuppressionPolicyInputSelectorFields(BaseModel):
    trigger_ancestors: Optional[List[str]] = Field(
        alias=undash(lib.SUP_POL_CMD_TRIG_ANCESTORS)
    )
    trigger_class: Optional[List[str]] = Field(
        alias=undash(lib.SUP_POL_CMD_TRIG_CLASS)
    )
    users: Optional[List[str]] = Field(alias=undash(lib.SUP_POL_CMD_USERS))
    interactive_users: Optional[List[str]] = Field(
        alias=undash(lib.SUP_POL_CMD_INT_USERS)
    )
    non_interactive_users: Optional[List[str]] = Field(
        alias=undash(lib.SUP_POL_CMD_N_INT_USERS)
    )


class CreateSuppressionPolicyHandlerInput(BaseModel):
    type: Literal[tuple(lib.SUPPRESSION_POL_TYPES)] = Field(
        title="The type of suppression policy to create"
    )
    object_uid: str | None = Field(title="UID of the object to suppress")
    scope_to_users: bool = Field(
        default=False, title="Scope the created policy to the relevant users"
    )
    selectors: CreateSuppressionPolicyInputSelectorFields = Field(
        default={}, title="Additional selectors to add to the policy"
    )
    name: str = Field(
        default="", title="Optional name for the suppression policy"
    )
    org_uid: str
    api_key: str
    api_url: str


class CreateSuppressionPolicyHandlerOutput(BaseModel):
    policy: str = Field(default="", title="The policy that was created")


@router.post("/create/suppressionpolicy")
def create_suppression_policy(
    i: CreateSuppressionPolicyHandlerInput,
) -> CreateSuppressionPolicyHandlerOutput:
    cmd_input = cmd_create.CreateSuppressionPolicyInput(
        i.type,
        i.object_uid,
        i.scope_to_users,
        i.name,
        i.org_uid,
        i.api_key,
        i.api_url,
        i.selectors.dict(by_alias=True, exclude_unset=True),
    )
    output = cmd_create.suppression_policy(cmd_input)
    return CreateSuppressionPolicyHandlerOutput(policy=output.policy)


# ------------------------------------------------------------------------------
# Create Guardian Policy
# ------------------------------------------------------------------------------

InputObject = Annotated[
    Union[
        schemas.GuardianBaselineModel,
        schemas.GuardianFingerprintModel,
        schemas.GuardianFingerprintGroupModel,
        schemas.UidListModel,
    ],
    Field(discriminator="kind"),
]


class CreateGuardianPolicyHandlerInput(BaseModel):
    input_objects: Json[List[InputObject]] = Field(
        title="The input object(s) used to build the policy"
    )
    name: str = Field(
        default="", title="Optional name for the guardian policy"
    )
    org_uid: str
    api_key: str
    api_url: str


class CreateGuardianPolicyHandlerOutput(BaseModel):
    policy: str = Field(default="", title="The policy that was created")


@router.post("/create/guardianpolicy")
def create_guardian_policy(
    i: CreateGuardianPolicyHandlerInput,
) -> CreateGuardianPolicyHandlerOutput:
    input_objects = [
        obj.dict(by_alias=True, exclude_unset=True) for obj in i.input_objects
    ]
    cmd_input = cmd_create.CreateGuardianPolicyInput(
        i.name,
        input_objects,
        i.org_uid,
        i.api_key,
        i.api_url,
    )
    output = cmd_create.guardian_policy(cmd_input)
    return CreateGuardianPolicyHandlerOutput(policy=output.policy)
