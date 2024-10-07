from fastapi import FastAPI
from contextlib import asynccontextmanager
from bangumi import coroutines, startBangumi, stopBangumi
from log import log

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    startBangumi()
    yield
    stopBangumi()
    log("Bangumi stopped")
app = FastAPI(lifespan=app_lifespan)