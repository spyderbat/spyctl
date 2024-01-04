import logging
import spyctl.config.configs as cfg
from fastapi import FastAPI

from .api import create, diff, merge, validate

app = FastAPI()


@app.get("/alive")
async def alive():
    return {"message": "Alive"}


@app.get("/")
async def root():
    return {"message": "Alive2"}


# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(
#     request: Request, exc: RequestValidationError
# ):
#     exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
#     logging.error(f"{request}: {exc_str}")
#     content = {"status_code": 422, "message": exc_str, "data": None}
#     return JSONResponse(
#         content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
#     )


app.include_router(create.router)
app.include_router(diff.router)
app.include_router(merge.router)
app.include_router(validate.router)
cfg.set_api_call()
