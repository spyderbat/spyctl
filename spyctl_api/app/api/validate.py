import spyctl.schemas_v2 as schemas
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field, Json

import app.app_lib as app_lib
import app.commands.validate as cmd_val

router = APIRouter(prefix="/api/v1")

# ------------------------------------------------------------------------------
# Validate Spyderbat Object
# ------------------------------------------------------------------------------


class ValidateHandlerInput(BaseModel):
    object: Json[schemas.SpyderbatObject] = Field(
        title="The object to be validated."
    )


class ValidateHandlerOutput(BaseModel):
    invalid_message: str = Field(
        title="Message if the object is invalid,"
        " empty string if object is valid"
    )


@router.post("/validate")
def validate(
    i: ValidateHandlerInput, background_tasks: BackgroundTasks
) -> ValidateHandlerOutput:
    background_tasks.add_task(app_lib.flush_spyctl_log_messages)
    validate_input = cmd_val.ValidateInput(i.object.dict(by_alias=True))
    output = cmd_val.validate(validate_input)
    return ValidateHandlerOutput(invalid_message=output.invalid_message)
