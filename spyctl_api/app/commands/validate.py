from dataclasses import dataclass
from typing import Dict

import spyctl.schemas_v2 as schemas

import app.app_lib as app_lib

# ------------------------------------------------------------------------------
# Validate Spyderbat Object
# ------------------------------------------------------------------------------


@dataclass
class ValidateInput:
    object: Dict


@dataclass
class ValidateOutput:
    invalid_message: str


def validate(i: ValidateInput) -> ValidateOutput:
    if not schemas.valid_object(i.object):
        invalid_msg = app_lib.flush_spyctl_log_messages()
    else:
        invalid_msg = ""
    return ValidateOutput(invalid_message=invalid_msg)
