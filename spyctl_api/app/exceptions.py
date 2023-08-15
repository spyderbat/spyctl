import traceback

from fastapi import HTTPException


def bad_request(msg: str = None):
    detail = "Bad Request."
    if msg:
        detail += f" {msg}"
    raise HTTPException(400, detail=detail)


def internal_server_error(msg: str = None):
    s = traceback.format_exc()
    detail = "Internal Server Error." + s + "\n"
    if msg:
        detail += f" {msg}"
    raise ValueError(detail)
