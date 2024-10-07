import feedparser
import requests
import os
from model import Session
from model import Bangumi, TV, Movie, Torrent, TorrentStatus, TorrentType, SRMissionStatus
import config
from urllib.parse import urlparse
import re
import datetime
import asyncio
import qb
import libtorrent as lt
from log import log
from typing import Dict
from fastapi.responses import JSONResponse
from typing import Tuple
from notification import sendNotificationFinish, sendNotificationWarning
from sr_manager import mission_manager

req_session = requests.Session()
req_session.proxies = proxies=config.proxies

coroutines : Dict[int, asyncio.Task] = {}
event_loop_bangumi : asyncio.AbstractEventLoop = None

def get_filename_from_url(url: str):
    parsed_url = urlparse(url)
    filename_with_extension = os.path.basename(parsed_url.path)
    filename_without_extension, _ = os.path.splitext(filename_with_extension)
    return filename_without_extension

def extract_episode_number(rule: str, string: str, need_epi: bool = True):
    match = re.search(rule, string)
    if match:
        if need_epi:
            return match.group(1)  # Returns the first group
        return match.group(0)  # Returns the whole match
    else:
        return None

def convert_to_magnet(url: str) -> Tuple[str, str]:
    """
    @param url: The url of the torrent file
    @return: A tuple of (hash, magnet)
    """
    if url.startswith('magnet:'):
        params = lt.parse_magnet_uri(url)
        return params['info_hash'], url
    
    torrent_response = req_session.get(url)
    if torrent_response.status_code != 200:
        raise Exception(f"Failed to download torrent file {url}.")
    # save to temp file
    import tempfile
    temp_file_path = None
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(torrent_response.content)
        temp_file_path = temp_file.name

    try:
        info = lt.torrent_info(temp_file_path)
        info_hash = str(info.info_hash())
        magnet = lt.make_magnet_uri(info)
        return info_hash, magnet
    finally:
        os.remove(temp_file_path)

async def TrackBangumi(bangumi_id : int):
    with Session() as session:
        bangumi = session.query(Bangumi).filter_by(id=bangumi_id).first()
        if bangumi is None:
            return
    log(f"Starting {bangumi.id}")
    while datetime.datetime.now() < bangumi.expire_time:
        log(f"Starting a new coroutine of {bangumi.name}")
        try:
            response = req_session.post(bangumi.rss)
            if response.status_code != 200:
                raise Exception(f"{bangumi.name} Failed to make requests to RSS feed.")
            feed = feedparser.parse(response.text)
            for entry in feed.entries:
                # print(entry.title)
                episode_raw = extract_episode_number(bangumi.regex_rule_episode, entry.title)
                if episode_raw == None: continue
                else: episode_raw = int(episode_raw)

                with Session() as session:
                    existing_torrent = session.query(Torrent).filter_by(bangumi_id=bangumi.id,
                                                                        episode_raw=episode_raw).first()
                    if existing_torrent != None:
                        if existing_torrent.status != TorrentStatus.DOWNLOADED:
                            hash_code = existing_torrent.hash
                            status, rate = qb.GetTorrentStatus(hash_code)
                            if status == "Not Added":
                                log(f"Torrent {hash_code} is not added, re-adding")
                                try:
                                    qb.AddTorrent(existing_torrent.id)
                                except Exception as e:
                                    log(f"Failed to readd torrent {hash_code} to qbittorrent: {str(e)}")
                            elif rate == 1:
                                log(f"Torrent {hash_code} is downloaded, marking as downloaded")
                                existing_torrent.status = TorrentStatus.DOWNLOADED
                                session.commit()
                        continue

                hash_code = None
                magnet = None
                for enclosure in entry.enclosures:
                    if enclosure['type'] == 'application/x-bittorrent':
                        try:
                            hash_code, magnet = convert_to_magnet(enclosure['url'])
                        except Exception as e:
                            log(f"Failed to convert torrent file to magnet: {str(e)}")
                        break
                if hash_code == None: continue
                log(f"Found a new torrent for {bangumi.name} episode {episode_raw} => {episode_raw + bangumi.episode_offset} with hash {hash_code} and magnet {magnet}")

                with Session() as session:
                    new_torrent = Torrent(
                        status=TorrentStatus.DOWNLOADING,
                        torrent_type=TorrentType.TV_SEASON,
                        episode_raw=episode_raw,
                        hash=hash_code,
                        bangumi_id=bangumi.id,
                        magnet=magnet
                    )
                    session.add(new_torrent)
                    session.commit()
                    session.refresh(new_torrent)
                
                log(f"Adding torrent {hash_code} to qbittorrent")
                try:
                    qb.AddTorrent(new_torrent.id)
                except Exception as e:
                    log(f"Failed to add torrent {hash_code} to qbittorrent")
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
            with Session() as session:
                bangumi = session.query(Bangumi).filter_by(id=bangumi.id).first()
                if bangumi is None:
                    raise asyncio.CancelledError()
        except asyncio.CancelledError as e:
            log(f"OVER CANCEL {bangumi.name}")
            return
    log(f"OVER {bangumi.name}")

async def DeleteBangumi(bangumi_id: int):
    with Session() as session:
        bangumi = session.query(Bangumi).filter_by(id=bangumi_id).first()
        if bangumi is None:
            return JSONResponse(status_code=404, content={'message': 'Bangumi not found.'})
        if bangumi_id in coroutines:
            coroutines[bangumi_id].cancel()
            del coroutines[bangumi_id]
        session.delete(bangumi)
        session.commit()
    return JSONResponse(status_code=200, content={'message': 'Bangumi deleted.'})

async def DeleteTV(tv_id: int):
    with Session() as session:
        tv = session.query(TV).filter_by(id=tv_id).first()
        if tv is None:
            return JSONResponse(status_code=404, content={'message': 'TV not found.'})
        session.delete(tv)
        session.commit()
    return JSONResponse(status_code=200, content={'message': 'TV deleted.'})

async def DeleteMovie(movie_id: int):
    with Session() as session:
        movie = session.query(Movie).filter_by(id=movie_id).first()
        if movie is None:
            return JSONResponse(status_code=404, content={'message': 'Movie not found.'})
        session.delete(movie)
        session.commit()
    return JSONResponse(status_code=200, content={'message': 'Movie deleted.'})

async def _StartNewBangumi(bangumi_id: int):
    with Session() as session:
        bangumi = session.query(Bangumi).filter_by(id=bangumi_id).first()
        if bangumi is not None:
            coroutines[bangumi_id] = event_loop_bangumi.create_task(TrackBangumi(bangumi_id))
    
async def AddNewBangumi(name: str, season: str, rss: str, regex_rule_episode: str, episode_offset: int, need_super_resolution: bool, checked: bool):
    with Session() as session:
        if not checked and session.query(Bangumi).filter_by(name=name, season=season).first() is not None:
            return JSONResponse(status_code=400, content={'message': 'Bangumi already exists.'})
        new_bangumi = Bangumi(
            name=name,
            season=season,
            rss=rss,
            regex_rule_episode=regex_rule_episode,
            episode_offset=episode_offset,
            need_super_resolution=need_super_resolution,
            expire_time=datetime.datetime.now() + datetime.timedelta(days=30),
            last_update_time=datetime.datetime.now()
        )
        session.add(new_bangumi)
        session.commit()
        session.refresh(new_bangumi)
        event_loop_bangumi.call_soon_threadsafe(event_loop_bangumi.create_task, _StartNewBangumi(new_bangumi.id))
        while new_bangumi.id not in coroutines:
            await asyncio.sleep(0.1)

async def QueryBangumiStatus(bangumi_id: int):
    if bangumi_id in coroutines:
        return "Running"
    return "Stopped"

async def AddNewTV(name:str, season:str, torrent_url:str, regex_rule_episode:str, episode_offset:int, need_super_resolution:bool, checked:bool):
    with Session() as session:
        if not checked and session.query(TV).filter_by(name=name, season=season).first():
            return JSONResponse(status_code=400, content={'message': 'TV already exists.'})
        hash_code, magnet = convert_to_magnet(torrent_url)
        new_torrent = Torrent(
            status = TorrentStatus.DOWNLOADING,
            torrent_type = TorrentType.TV,
            hash = hash_code,
            magnet = magnet
        )
        session.add(new_torrent)
        session.commit()
        session.refresh(new_torrent)

        new_tv = TV(
            name=name,
            season=season,
            torrent_url=torrent_url,
            regex_rule_episode=regex_rule_episode,
            episode_offset=episode_offset,
            need_super_resolution=need_super_resolution,
            tv_id=new_torrent.id
        )
        session.add(new_tv)
        session.commit()
        session.refresh(new_tv)

        try:
            qb.AddTorrent(new_torrent.id)
        except Exception as e:
            log(f"Failed to add torrent {hash_code} to qbittorrent: {str(e)}")
        return JSONResponse(status_code=200)

async def AddNewMovie(name:str, torrent_url:str, regex:str, need_super_resolution:bool, checked:bool):
    with Session() as session:
        if not checked and session.query(Movie).filter_by(name=name).first():
            return JSONResponse(status_code=400, content={'message': 'Movie already exists.'})
        hash_code, magnet = convert_to_magnet(torrent_url)
        new_torrent = Torrent(
            status = TorrentStatus.DOWNLOADING,
            torrent_type = TorrentType.MOVIE,
            hash = hash_code,
            magnet = magnet
        )
        session.add(new_torrent)
        session.commit()
        session.refresh(new_torrent)
        new_movie = Movie(
            name=name,
            torrent_url=torrent_url,
            regex=regex,
            need_super_resolution=need_super_resolution,
            movie_id=new_torrent.id
        )
        session.add(new_movie)
        session.commit()
        session.refresh(new_movie)

        try:
            qb.AddTorrent(new_torrent.id)
        except Exception as e:
            log(f"Failed to add torrent {hash_code} to qbittorrent: {str(e)}")
        return JSONResponse(status_code=200)

def is_video_file(filename:str) -> bool:
    VIDEO_EXTENSIONS = ['.mp4', '.mkv']
    return filename.endswith(tuple(VIDEO_EXTENSIONS))

def is_subtitle_file(filename:str) -> bool:
    SUBTITLE_EXTENSIONS = ['.srt']
    return filename.endswith(tuple(SUBTITLE_EXTENSIONS))

def match_regex(regex: str, string: str) -> bool:
    return re.match(regex, string) is not None

async def DownloadFinished(hash: str, torrent_path: str):
    with Session() as session:
        torrent = session.query(Torrent).filter_by(hash=hash).first()
        if torrent is None:
            return JSONResponse(status_code=404, content={'message': 'Torrent not found.'})
        torrent.status = TorrentStatus.DOWNLOADED
        session.commit()
        if torrent.torrent_type == TorrentType.TV:
            tv = session.query(TV).filter_by(tv_id=torrent.id).first()
            if tv is None:
                return JSONResponse(status_code=500, content={'message': 'TV not found.'})
            target_path = os.path.join(config.tv_save_path, tv.name, f'Season {tv.season}')
            torrent_path = os.path.join(config.mounted_path, torrent_path)
            new_filename = None
            if os.path.isfile(torrent_path):
                return JSONResponse(status_code=500, content={'message': 'TV should be a directory.'})
            for root, _, files in os.walk(torrent_path):
                for filename in files:
                    if is_video_file(filename) or is_subtitle_file(filename):
                        episode = extract_episode_number(tv.regex_rule_episode, filename, need_epi=True)
                        if episode is None:
                            continue
                        src_file = os.path.join(root, filename)
                        ext = os.path.splitext(filename)[1]
                        new_filename = f"{tv.name} S{str(tv.season).zfill(2)}E{str(episode + tv.episode_offset).zfill(2)}{ext}"
                        dst_file = os.path.join(target_path, new_filename)
                        os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                        os.link(src_file, dst_file)
            if tv.need_super_resolution:
                mission_manager.add_mission(torrent.id, new_filename, new_filename, 'hevc_nvenc')
            else:
                sendNotificationFinish('TV', new_filename, 'download', target_path)
            return JSONResponse(status_code=200, content={'message': 'TV downloaded.'})
        elif torrent.torrent_type == TorrentType.MOVIE:
            movie = session.query(Movie).filter_by(movie_id=torrent.id).first()
            if movie is None:
                return JSONResponse(status_code=500, content={'message': 'Movie not found.'})
            target_path = config.movie_save_path
            torrent_path = os.path.join(config.mounted_path, torrent_path)
            new_filename = None
            if os.path.isfile(torrent_path):
                ext = os.path.splitext(torrent_path)[1]
                new_filename = f"{movie.name}{ext}"
                dst_file = os.path.join(target_path, new_filename)
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                os.link(torrent_path, dst_file)
            else:
                for root, _, files in os.walk(torrent_path):
                    for filename in files:
                        if is_video_file(filename) or is_subtitle_file(filename):
                            if extract_episode_number(movie.file_regex, filename, need_epi=False):
                                src_file = os.path.join(root, filename)
                                ext = os.path.splitext(filename)[1]
                                new_filename = f"{movie.name}{ext}"
                                dst_file = os.path.join(target_path, new_filename)
                                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                                os.link(src_file, dst_file)
            if movie.need_super_resolution:
                mission_manager.add_mission(torrent.id, new_filename, new_filename, 'hevc_nvenc')
            else:
                sendNotificationFinish('Movie', new_filename, 'download', target_path)
            return JSONResponse(status_code=200, content={'message': 'Movie downloaded.'})
        elif torrent.torrent_type == TorrentType.TV_SEASON:
            bangumi = session.query(Bangumi).filter_by(id=torrent.bangumi_id).first()
            if bangumi is None:
                return JSONResponse(status_code=500, content={'message': 'Bangumi not found.'})
            target_path = os.path.join(config.bangumi_save_path, bangumi.name, f'Season {bangumi.season}')
            torrent_path = os.path.join(config.mounted_path, torrent_path)
            new_filename = None
            dst_video_file = None
            if os.path.isfile(torrent_path):
                src_file = torrent_path
                ext = os.path.splitext(torrent_path)[1]
                new_filename = f"{bangumi.name} S{str(bangumi.season).zfill(2)}E{str(torrent.episode_raw + bangumi.episode_offset).zfill(2)}{ext}"
                dst_file = os.path.join(target_path, new_filename)
                dst_video_file = dst_file
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                if os.path.exists(dst_file):
                    os.remove(dst_file)
                os.link(src_file, dst_file)
            else:
                for root, _, files in os.walk(torrent_path):
                    for filename in files:
                        if is_video_file(filename) or is_subtitle_file(filename):
                            src_file = os.path.join(root, filename)
                            ext = os.path.splitext(filename)[1]
                            new_filename = f"{bangumi.name} S{str(bangumi.season).zfill(2)}E{str(torrent.episode_raw + bangumi.episode_offset).zfill(2)}{ext}"
                            dst_file = os.path.join(target_path, new_filename)
                            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                            if os.path.exists(dst_file):
                                os.remove(dst_file)
                            if is_video_file(filename):
                                dst_video_file = dst_file
                            os.link(src_file, dst_file)
            if bangumi.need_super_resolution:
                log(f"Adding super resolution mission for {new_filename}")
                mission_manager.add_mission(torrent.id, dst_video_file, dst_video_file, 'hevc_nvenc')
            else:
                sendNotificationFinish('Bangumi', new_filename, 'download', target_path)
            return JSONResponse(status_code=200, content={'message': 'Bangumi downloaded.'})
        return JSONResponse(status_code=500, content={'message': 'Unknown torrent type.'})

_stopped = False

import threading
async def BangumiMain(start_signal: threading.Event):
    with Session() as session:
        bangumis = session.query(Bangumi).all()
        for bangumi in bangumis:
            task = asyncio.create_task(TrackBangumi(bangumi.id))
            coroutines[bangumi.id] = task
            # event_loop_bangumi.call_soon_threadsafe(asyncio.create_task, task)
        start_signal.set()
    while not _stopped:
        await asyncio.sleep(1)

def startBangumi():
    global track_thread
    global event_loop_bangumi
    event_loop_bangumi = asyncio.new_event_loop()
    bangumi_started = threading.Event()
    def run_bangumi_main():
        asyncio.set_event_loop(event_loop_bangumi)
        event_loop_bangumi.run_until_complete(BangumiMain(bangumi_started))
    track_thread = threading.Thread(target=run_bangumi_main)
    track_thread.start()
    bangumi_started.wait()

def stopBangumi():
    global _stopped
    for coroutine in coroutines.values():
        if not coroutine.done():
            coroutine.cancel()
    _stopped = True
