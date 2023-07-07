from fastapi import FastAPI
import spyctl.config.configs as cfg

from .api import create, merge

app = FastAPI()
app.include_router(create.router)
app.include_router(merge.router)
cfg.set_api_call()
