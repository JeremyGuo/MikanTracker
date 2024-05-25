import feedparser
import time
import requests
import sqlite3
import os
import db
import config
from urllib.parse import urlparse
import re
import datetime
import asyncio
import qb
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import threading

# http://127.0.0.1:20172
session = requests.Session()
session.proxies = proxies=config.proxies

def get_filename_from_url(url):
    parsed_url = urlparse(url)
    filename_with_extension = os.path.basename(parsed_url.path)
    filename_without_extension, _ = os.path.splitext(filename_with_extension)
    return filename_without_extension

def extract_episode_number(rule, string):
    match = re.search(rule, string)
    if match:
        return match.group(1)  # Returns the first group
    else:
        return None

coroutines = {}

async def TrackBangumi(bangumi : db.Bangumi):
    while datetime.datetime.now() < bangumi.expire_time:
        print(f"START {bangumi.name}")
        try:
            response = session.post(bangumi.rss)
            if response.status_code != 200:
                raise "Failed to make requests"
            feed = feedparser.parse(response.text)
            for entry in feed.entries:
                # print(entry.title)
                ep_idx = extract_episode_number(bangumi.regex_rule_episode, entry.title)
                if ep_idx == None: continue
                else: ep_idx = int(ep_idx)

                existing_torrent = db.session.query(db.Magnet).filter_by(bangumi_id=bangumi.id, episode=ep_idx).first()
                if existing_torrent != None: continue

                hash_code = None
                for enclosure in entry.enclosures:
                    if enclosure['type'] == 'application/x-bittorrent':
                        hash_code = get_filename_from_url(enclosure['url'])
                        break
                if hash_code == None: continue

                new_torrent = db.Magnet(
                    status=db.TorrentStatus.DOWNLOADING,
                    bangumi_id=bangumi.id,
                    episode=ep_idx,
                    hash=hash_code
                )
                qb.AddTorrent(config.magnet_template.format(hash_code), f'Ep:{ep_idx},Name:{bangumi.name},Season:{bangumi.season}', hash_code)
                db.session.add(new_torrent)
                db.session.commit()

                bangumi.last_update_time = datetime.datetime.now()
                bangumi.expire_time = datetime.datetime.now() + datetime.timedelta(days=30)
                db.session.commit()
        except Exception as e:
            print(str(e))
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError as e:
            print(f"OVER CANCEL {bangumi.name}")
            return
    print(f"OVER {bangumi.name}")

async def DeleteBangumi(bangumi_id):
    bangumi = db.session.query(db.Bangumi).get(bangumi_id)
    if bangumi is None:
        raise Exception("Bangumi not found")

    if bangumi_id in coroutines:
        coroutines[bangumi_id].cancel()
        del coroutines[bangumi_id]

    for torrent in bangumi.torrents:
        db.session.delete(torrent)
    db.session.delete(bangumi)
    db.session.commit()
    
async def UpdateBangumi(bangumi_id, name, season, rss, regex_rule_episode):
    if bangumi_id in coroutines:
        coroutines[bangumi_id].cancel()
        del coroutines[bangumi_id]

    bangumi = db.session.query(db.Bangumi).get(bangumi_id)
    if bangumi is None:
        raise Exception("Bangumi not found")

    bangumi.name = name
    bangumi.season = season
    bangumi.rss = rss
    bangumi.regex_rule_episode = regex_rule_episode

    db.session.commit()

    task = asyncio.create_task(TrackBangumi(bangumi))
    coroutines[bangumi.id] = task
    
async def AddNewBangumi(name, season, rss, regex_rule_episode):
    existing_bangumi = db.session.query(db.Bangumi).filter_by(name=name, season=season).first()
    if existing_bangumi:
        raise Exception(f'Bangumi with name "{name}" and season "{season}" already exists.')

    new_bangumi = db.Bangumi(
        name=name,
        season=int(season),
        rss=rss,
        regex_rule_episode=regex_rule_episode,
        expire_time=datetime.datetime.now() + datetime.timedelta(days=30),
        last_update_time=datetime.datetime.now()
    )
    db.session.add(new_bangumi)
    db.session.commit()

    task = asyncio.create_task(TrackBangumi(new_bangumi))
    coroutines[new_bangumi.id] = task

app = FastAPI()
templates = Jinja2Templates(directory="templates")

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
    bangumis = db.session.query(db.Bangumi).all()
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
    bangumi = db.session.query(db.Bangumi).filter(db.Bangumi.id == bangumi_id).first()
    bangumi_data = bangumi.to_dict()
    for e in bangumi_data['torrents']:
        status = qb.GetTorrentStatus(e['hash'])
        e['status'] = status
    return templates.TemplateResponse("track.html", {"request": request, "bangumi": bangumi_data})

async def main():
    print("Starting main")
    bangumis = db.session.query(db.Bangumi).all()
    for bangumi in bangumis:
        task = asyncio.create_task(TrackBangumi(bangumi))
        coroutines[bangumi.id] = task
    while True:
        await asyncio.sleep(3600)

def run_main():
    asyncio.run(main())

if __name__ == "__main__":
    track_thread = threading.Thread(target=run_main, daemon=True)
    track_thread.start()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
