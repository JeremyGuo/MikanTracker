import feedparser
import time
import requests
import sqlite3
import os
import db
from db import Session
import config
from urllib.parse import urlparse
import re
import datetime
import asyncio
import qb
import libtorrent as lt
from log import log

# http://127.0.0.1:20172
req_session = requests.Session()
req_session.proxies = proxies=config.proxies

event_loop_bangumi = None
coroutines = {}

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

async def TrackBangumi(bangumi : db.Bangumi):
    log(f"Starting {bangumi.name}")
    while datetime.datetime.now() < bangumi.expire_time:
        log(f"Starting a new coroutine of {bangumi.name}")
        try:
            response = req_session.post(bangumi.rss)
            if response.status_code != 200:
                raise Exception(f"{bangumi.name} Failed to make requests to RSS feed.")
            feed = feedparser.parse(response.text)
            for entry in feed.entries:
                # print(entry.title)
                ep_idx = extract_episode_number(bangumi.regex_rule_episode, entry.title)
                if ep_idx == None: continue
                else: ep_idx = int(ep_idx)

                with Session() as session:
                    existing_torrent = session.query(db.Magnet).filter_by(bangumi_id=bangumi.id, episode=ep_idx).first()
                    if existing_torrent != None:
                        hash_code = existing_torrent.hash
                        status, rate = qb.GetTorrentStatus(hash_code)
                        if status == "Not Added":
                            log(f"Torrent {hash_code} is not added, re-adding")
                            qb.AddTorrent(config.magnet_template.format(hash_code), f'Ep:{ep_idx},Name:{bangumi.name},Season:{bangumi.season}', hash_code)
                        continue

                hash_code = None
                for enclosure in entry.enclosures:
                    if enclosure['type'] == 'application/x-bittorrent':
                        # Download the torrent file and convert the file to the hash_code
                        torrent_response = req_session.get(enclosure['url'])
                        if torrent_response.status_code != 200:
                            raise Exception(f"{bangumi.name} Failed to download torrent file {enclosure['url']}.")
                        # save to temp file
                        import tempfile
                        temp_file_path = None
                        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                            temp_file.write(torrent_response.content)
                            temp_file_path = temp_file.name
                        
                        try:
                            # 使用 libtorrent 读取种子文件
                            info = lt.torrent_info(temp_file_path)
                            info_hash = str(info.info_hash())
                            hash_code = info_hash
                        finally:
                            # 删除临时文件
                            os.remove(temp_file_path)
                        break
                if hash_code == None: continue
                log(f"Found a new torrent for {bangumi.name} episode {ep_idx} with hash {hash_code}")

                new_torrent = db.Magnet(
                    status=db.TorrentStatus.DOWNLOADING,
                    bangumi_id=bangumi.id,
                    episode=ep_idx,
                    hash=hash_code
                )
                log(f"Adding torrent {hash_code} to qbittorrent")
                qb.AddTorrent(config.magnet_template.format(hash_code), f'Ep:{ep_idx},Name:{bangumi.name},Season:{bangumi.season}', hash_code)
                log(f"Added torrent {hash_code} to qbittorrent")

                with Session() as session:
                    session.add(new_torrent)
                    session.commit()

                    bangumi.last_update_time = datetime.datetime.now()
                    bangumi.expire_time = datetime.datetime.now() + datetime.timedelta(days=30)
                    session.commit()
            log(f"End a loop of {bangumi.name}")
        except Exception as e:
            log(f"{bangumi.name} {str(e)}")
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError as e:
            log(f"OVER CANCEL {bangumi.name}")
            return
    log(f"OVER {bangumi.name}")

async def DeleteBangumi(bangumi_id):
    with Session() as session:
        bangumi = session.query(db.Bangumi).get(bangumi_id)
        if bangumi is None:
            raise Exception("Bangumi not found")
        if bangumi_id in coroutines:
            coroutines[bangumi_id].cancel()
            del coroutines[bangumi_id]
        session.delete(bangumi)
        session.commit()

async def StartNewBangumi(bangumi):
    coroutines[bangumi.id] = asyncio.create_task(TrackBangumi(bangumi))
    
async def AddNewBangumi(name, season, rss, regex_rule_episode):
    with Session() as session:
        existing_bangumi = session.query(db.Bangumi).filter_by(name=name, season=season).first()
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
        session.add(new_bangumi)
        session.commit()
    event_loop_bangumi.call_soon_threadsafe(asyncio.create_task, StartNewBangumi(new_bangumi))
    while new_bangumi.id not in coroutines:
        await asyncio.sleep(0.1)

import threading
async def BangumiMain(start_signal: threading.Event):
    print("Starting main")
    with Session() as session:
        bangumis = session.query(db.Bangumi).all()
        for bangumi in bangumis:
            task = asyncio.create_task(TrackBangumi(bangumi))
            coroutines[bangumi.id] = task
        start_signal.set()