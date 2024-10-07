import threading
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from model import Session, Bangumi, TV, Movie, Torrent
import qb
from pydantic import BaseModel

from bangumi import coroutines, DownloadFinished
from bangumi import DeleteBangumi, AddNewBangumi
from bangumi import DeleteTV, AddNewTV
from bangumi import DeleteMovie, AddNewMovie
templates = Jinja2Templates(directory="templates")

# A signal method for signaling main thread main executed
import asyncio
from app import *
from api import *

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    with Session() as session:
        return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
