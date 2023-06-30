from fastapi import FastAPI
import spyctl.config.configs as cfg

from .api import create

app = FastAPI()
app.include_router(create.router)
cfg.set_api_call()
