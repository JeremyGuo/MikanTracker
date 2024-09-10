import threading
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from db import Session
import db
import qb

from bangumi import DeleteBangumi, AddNewBangumi, coroutines
templates = Jinja2Templates(directory="templates")

# A signal method for signaling main thread main executed
import asyncio
from bangumi import BangumiMain

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    event_loop_bangumi = asyncio.new_event_loop()
    bangumi_started = threading.Event()
    def run_bangumi_main():
        asyncio.set_event_loop(event_loop_bangumi)
        event_loop_bangumi.call_soon_threadsafe(asyncio.create_task, BangumiMain(bangumi_started))
        event_loop_bangumi.run_forever()
    track_thread = threading.Thread(target=run_bangumi_main)
    track_thread.start()
    bangumi_started.wait()
    yield
    for coroutine in coroutines.values():
        if not coroutine.done():
            coroutine.cancel()
    event_loop_bangumi.stop()
app = FastAPI(lifespan=app_lifespan)

@app.post("/delete_bangumi", response_class=RedirectResponse)
async def delete_bangumi(bangumi_id: int = Form(...)):
    await DeleteBangumi(bangumi_id)
    return RedirectResponse("/", status_code=303)

@app.post("/add_bangumi", response_class=RedirectResponse)
async def add_bangumi(name: str = Form(...), season: int = Form(...), rss: str = Form(...), regex: str = Form(...)):
    await AddNewBangumi(name, season, rss, regex)
    return RedirectResponse("/", status_code=303)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    with Session() as session:
        bangumis = session.query(db.Bangumi).all()
        bangumi_data = [b.to_dict() for b in bangumis]
        for b in bangumi_data:
            status = "Running"
            if not (b['id'] in coroutines): status = 'Not Started'
            elif coroutines[b['id']].done():
                if coroutines[b['id']].cancelled(): status = 'Cancelled'
                else: status = 'Done'
            b['coroutine_status'] = status
        return templates.TemplateResponse("index.html", {"request": request, "bangumis": bangumi_data})

@app.get("/track/{bangumi_id}", response_class=HTMLResponse)
async def track_bangumi(request: Request, bangumi_id: int):
    with Session() as session:
        bangumi = session.query(db.Bangumi).filter(db.Bangumi.id == bangumi_id).first()
        bangumi_data = bangumi.to_dict()
        for e in bangumi_data['torrents']:
            status, rate = qb.GetTorrentStatus(e['hash'])
            e['status'] = status
        return templates.TemplateResponse("track.html", {"request": request, "bangumi": bangumi_data})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
