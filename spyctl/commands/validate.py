import spyctl.cli as cli
import spyctl.spyctl_lib as lib
from typing import List, Dict, Union, Any
import spyctl.schemas_v2 as schemas
import json


def handle_validate(file):
    if file:
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
