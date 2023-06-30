from fastapi import HTTPException


def bad_request(msg: str = None):
    detail = "Bad Request."
    if msg:
        detail += f" {msg}"
    raise HTTPException(400, detail=detail)


def internal_server_error(msg: str = None):
    detail = "Internal Server Error."
    if msg:
        detail += f" {msg}"
    raise HTTPException(500, detail=detail)
