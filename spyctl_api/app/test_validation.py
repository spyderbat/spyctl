from pydantic import BaseModel, Json
from typing import List, Dict

import json

OBJ = json.loads(
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
        "conns": [{"ips": ["127.0.0.1"], "procs": ["foo_1"]}],
    }
)

BAD_OBJ_1 = "bad object"
BAD_OBJ_2 = ["bad object"]


class InputModel(BaseModel):
    obj: Json[Dict | List[dict]]


class FullModel(BaseModel):
    version: int
    type: str


def test_validation():
    _ = InputModel(obj=OBJ)
    _ = InputModel(obj=BAD_OBJ_1)
    _ = InputModel(obj=BAD_OBJ_2)
