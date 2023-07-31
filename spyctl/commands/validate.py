import json
from typing import IO, Any, Dict, List, Union

import spyctl.api as api
import spyctl.config.configs as cfg
import spyctl.cli as cli
import spyctl.schemas_v2 as schemas
import spyctl.spyctl_lib as lib


def handle_validate(file: IO, do_api=False):
    if file and do_api:
        ctx = cfg.get_current_context()
        resrc_data = lib.load_file_for_api_test(file)
        data = {"object": json.dumps(resrc_data)}
        invalid_message = api.api_validate(*ctx.get_api_data(), data)
        if not invalid_message:
            kind = resrc_data[lib.KIND_FIELD]
            cli.try_log(f"{kind} valid!")
        else:
            print(invalid_message)
    elif file:
        resrc_data = lib.load_resource_file(file, validate_cmd=True)
        if isinstance(resrc_data, list):
            cli.try_log("List of objects valid!")
        else:
            kind = resrc_data[lib.KIND_FIELD]
            cli.try_log(f"{kind} valid!")


def validate_json(json_data: Union[str, Any]) -> bool:
    if isinstance(json_data, str):
        obj = json.loads(json_data)
    else:
        obj = json_data
    if isinstance(obj, list):
        return validate_list(obj)
    elif isinstance(obj, dict):
        return validate_object(obj)
    else:
        cli.err_exit(
            "Invalid Object to Validate, expect dictionary or list of"
            " dictionaries."
        )


def validate_list(objs: List):
    for i, obj in enumerate(objs):
        if isinstance(obj, Dict):
            if not validate_object(obj):
                cli.try_log(f"Object at index {i} is invalid. See logs.")
                return False
        else:
            cli.try_log(f"Invalid Object at index {i}, expect dictionary.")
            return False
    return True


def validate_object(obj: dict) -> bool:
    return schemas.valid_object(obj)
