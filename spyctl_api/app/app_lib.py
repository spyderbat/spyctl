import spyctl.spyctl_lib as s_lib
import spyctl.config.configs as cfg
from fastapi import HTTPException


def flush_spyctl_log_messages() -> str:
    messages = s_lib.flush_log_var() + "\n" + s_lib.flush_err_var()
    return messages


def generate_spyctl_context(
    org_uid: str, api_key: str, api_url: str
) -> cfg.Context:
    if not input.org_uid or not input.api_key or not input.api_url:
        raise HTTPException(
            status_code=400,
            detail="Bad Request. Missing org_uid, api_key, and/or api_url",
        )
    spyctl_ctx = cfg.create_temp_secret_and_context(
        input.org_uid, input.api_key, input.api_url
    )
    return spyctl_ctx
