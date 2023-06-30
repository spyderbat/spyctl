from dataclasses import dataclass, field

import spyctl.commands.create as spyctl_create
import spyctl.config.configs as cfg
import spyctl.spyctl_lib as lib
from fastapi import HTTPException
import json
import app_lib

# ------------------------------------------------------------------------------
# Create Suppression Policy
# ------------------------------------------------------------------------------


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
    i: CreateSuppressionPolicyInput,
) -> CreateSuppressionPolicyOutput:
    if i.type == lib.POL_TYPE_TRACE:
        return trace_suppression_policy(input)
    else:
        raise HTTPException(
            status_code=400,
            detail="Bad Request. Invalid suppression policy type.",
        )


def trace_suppression_policy(
    i: CreateSuppressionPolicyInput,
) -> CreateSuppressionPolicyOutput:
    spyctl_ctx = app_lib.generate_spyctl_context(
        i.org_uid, i.api_key, i.api_url
    )
    try:
        pol = spyctl_create.create_trace_suppression_policy(
            i.obj_uid,
            i.auto_generate_user_scope,
            i.name,
            ctx=spyctl_ctx,
            **i.selectors,
        )
    except HTTPException as e:
        raise e
    except Exception:
        msg = app_lib.flush_spyctl_log_messages()
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error. {msg}"
        )
    output = CreateSuppressionPolicyOutput(json.dumps(pol.as_dict()))
    return output


# ------------------------------------------------------------------------------
# Create Guardian Policy
# ------------------------------------------------------------------------------


@dataclass
class CreateGuardianPolicyInput:
    name: str = ""
    input_objs: str = ""
    org_uid: str = ""
    api_key: str = ""
    api_url: str = ""


@dataclass
class CreateGuardianPolicyOutput:
    policy: str


def guardian_policy(
    i: CreateGuardianPolicyInput,
) -> CreateGuardianPolicyOutput:
    spyctl_ctx = app_lib.generate_spyctl_context(
        i.org_uid, i.api_key, i.api_url
    )
    try:
        pol = spyctl_create.create_guardian_policy_from_json(
            i.name, i.input_objs, spyctl_ctx
        )
    except HTTPException as e:
        raise e
    except Exception:
        msg = app_lib.flush_spyctl_log_messages()
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error. {msg}"
        )
    output = CreateGuardianPolicyOutput(pol)
    return output
