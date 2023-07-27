import spyctl.config.configs as cfg
from fastapi import FastAPI

from .api import create, diff, merge, validate

app = FastAPI()


@app.get("/")
def root():
    return {}


@app.get("/alive")
def alive():
    return {"message": "Alive"}


app.include_router(create.router)
app.include_router(diff.router)
app.include_router(merge.router)
app.include_router(validate.router)
cfg.set_api_call()
