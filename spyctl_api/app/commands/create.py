from dataclasses import dataclass, field

import spyctl.commands.create as spyctl_create
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
from fastapi import HTTPException
import json


@dataclass
class CreateSuppressionPolicyInput:
    type: str
    obj_uid: str = ""
    auto_generate_user_scope: bool = False
    name: str = ""
    org_uid: str = ""
    api_key: str = ""
    api_url: str = ""
    selectors: dict = field(default_factory=dict)


@dataclass
class CreateSuppressionPolicyOutput:
    policy: str


def suppression_policy(
    input: CreateSuppressionPolicyInput,
) -> CreateSuppressionPolicyOutput:
    if input.type == lib.POL_TYPE_TRACE:
        return trace_suppression_policy(input)
    else:
        raise HTTPException(
            status_code=400,
            detail="Bad Request. Invalid suppression policy type.",
        )


def trace_suppression_policy(
    input: CreateSuppressionPolicyInput,
) -> CreateSuppressionPolicyOutput:
    if input.obj_uid:
        if not input.org_uid or not input.api_key or not input.api_url:
            raise HTTPException(
                status_code=400,
                detail="Bad Request. Missing org_uid, api_key, and/or api_url",
            )
        else:
            spyctl_ctx = cfg.create_temp_secret_and_context(
                input.org_uid, input.api_key, input.api_url
            )
    else:
        spyctl_ctx = None
    pol = spyctl_create.create_trace_suppression_policy(
        input.obj_uid,
        input.auto_generate_user_scope,
        input.name,
        ctx=spyctl_ctx,
        **input.selectors,
    )
    output = CreateSuppressionPolicyOutput(json.dumps(pol.as_dict()))
    return output
