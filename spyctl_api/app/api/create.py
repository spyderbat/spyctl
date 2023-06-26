import app.commands.create as cmd_create
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1")


class CreateSuppressionPolicyHandlerInput(BaseModel):
    type: str = Field(title="The type of suppression policy to create")
    obj_uid: str | None = Field(title="UID of the object to suppress")
    scope_to_users: bool = Field(
        default=False, title="Scope the created policy to the relevant users"
    )
    selectors: dict = Field(
        default={}, title="Additional selectors to add to the policy"
    )
    name: str = Field(
        default="", title="Optional name for the suppression policy"
    )
    org_uid: str | None
    api_key: str | None
    api_url: str | None


class CreateSuppressionPolicyHandlerOutput(BaseModel):
    policy: str = Field(default="", title="The policy that was created")


@router.post("/create/suppressionpolicy")
def create_suppression_policy(
    i: CreateSuppressionPolicyHandlerInput,
) -> CreateSuppressionPolicyHandlerOutput:
    cmd_input = cmd_create.CreateSuppressionPolicyInput(
        i.type,
        i.obj_uid,
        i.scope_to_users,
        i.name,
        i.org_uid,
        i.api_key,
        i.api_url,
        i.selectors,
    )
    output = cmd_create.suppression_policy(cmd_input)
    return CreateSuppressionPolicyHandlerOutput(policy=output.policy)
