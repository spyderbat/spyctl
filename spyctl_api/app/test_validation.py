from pydantic import (
    BaseModel,
    Json,
    validator,
    ValidationError,
    root_validator,
    PrivateAttr,
)
from typing import List, Dict, Any

import json

OBJ = json.dumps(
    {
        "version": 1,
        "type": "policy",
        "procs": [
            {
                "name": "blah",
                "id": "blah_1",
                "children": [{"name": "foo", "id": "foo_1"}],
            }
        ],
        "conns": [{"ips": ["127.0.0.1"], "procs": ["foo_12"]}],
    }
)

BAD_OBJ_1 = json.dumps("bad object")
BAD_OBJ_2 = json.dumps([{1: "bad object"}])

PROC_IDS = {}


class ProcModel(BaseModel):
    name: str
    id: str
    children: List["ProcModel"] = []

    @validator("id")
    def validate_no_duplicate_ids(cls, v):
        global PROC_IDS
        if v in PROC_IDS:
            raise ValueError(f"Duplicate id '{v}' detected.")
        PROC_IDS[v] = True
        return v

    class Config:
        copy_on_model_validation = "none"


class ConnModel(BaseModel):
    ips: List[str]
    procs: List[str]

    @validator("procs")
    def validate_id_exists(cls, v):
        for id in v:
            if id not in PROC_IDS:
                raise ValueError(f"No process found with id '{id}'.")
        return v

    class Config:
        copy_on_model_validation = "none"


class FullModel(BaseModel):
    version: int
    type: str
    procs: List[ProcModel]
    conns: List[ConnModel]

    def __init__(self, **data: Any):
        super().__init__(**data)
        global PROC_IDS
        PROC_IDS.clear()

    # @validator("procs", pre=True)
    # def inject_invalid_ids(cls, v):
    #     for proc in v:
    #         cls._proc_ids.update(cls.compute_proc_ids(proc))
    #     for proc in v:
    #         inject_invalid_ids(proc, cls._proc_ids)
    #     return v

    # @validator("conns", pre=True)
    # def inject_valid_ids(cls, v):
    #     for conn in v:
    #         conn["valid_ids"] = cls._proc_ids
    #     return v

    # @classmethod
    # def compute_proc_ids(self, proc: Dict | Any) -> Dict[str, bool]:
    #     if not isinstance(proc, Dict):
    #         return {}
    #     rv = {}
    #     id = proc.get("id")
    #     if id:
    #         rv[id] = True
    #     if "children" in proc:
    #         for child_proc in proc:
    #             rv.update(self.compute_proc_ids(child_proc))
    #     return rv


# def inject_invalid_ids(proc: Dict, invalid_ids: Dict):
#     proc["invalid_ids"] = invalid_ids
#     if "children" in proc:
#         for child_proc in proc["children"]:
#             inject_invalid_ids(child_proc, invalid_ids)


class InputModel(BaseModel):
    obj: Json[FullModel]

    class Config:
        copy_on_model_validation = "none"


def test_validation():
    print(InputModel.schema_json())
    try:
        _ = InputModel(obj=OBJ)
    except ValidationError as e:
        print(e)
    # _ = InputModel(obj=BAD_OBJ_1)
    # _ = InputModel(obj=BAD_OBJ_2)
