from fastapi import FastAPI
from contextlib import asynccontextmanager
from bangumi import coroutines, startBangumi, stopBangumi
from sr_manager import startSRMissionManager, stopSRMissionManager
from log import log

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    startSRMissionManager()
    startBangumi()
    yield
    stopBangumi()
    stopSRMissionManager()
    log("Bangumi stopped")
app = FastAPI(lifespan=app_lifespan)