from app import *
from fastapi import Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from model import Session, Bangumi, TV, Movie
from pydantic import BaseModel
from bangumi import DownloadFinished
from bangumi import DeleteBangumi, AddNewBangumi, QueryBangumiStatus
from bangumi import DeleteTV, AddNewTV
from bangumi import DeleteMovie, AddNewMovie

class FinishRequest(BaseModel):
    hash: str
    path: str
@app.post("/api/finish")
async def finish_bangumi(request: Request, finish_request: FinishRequest):
    log(f"Download finished: {finish_request.hash} {finish_request.path}")
    return await DownloadFinished(finish_request.hash, finish_request.path)

class BangumiAddRequest(BaseModel):
    name: str
    season: int
    rss: str
    regex: str
    episode_offset: int
    need_super_resolution: bool
    checked: bool
@app.post("/api/bangumi/add")
async def add_bangumi(request: Request, add_request: BangumiAddRequest):
    return await AddNewBangumi(add_request.name, add_request.season, add_request.rss, add_request.regex, add_request.episode_offset, add_request.need_super_resolution, add_request.checked)

class BangumiDelRequest(BaseModel):
    bangumi_id: int
@app.post("/api/bangumi/del")
async def delete_bangumi(request: Request, del_request: BangumiDelRequest):
    return await DeleteBangumi(del_request.bangumi_id)

class TVAddRequest(BaseModel):
    name: str
    season: str
    torrent_url: str
    regex_rule_episode: str
    episode_offset: int
    need_super_resolution: bool
    checked: bool
@app.post("/api/tv/add")
async def add_tv(request: Request, add_request: TVAddRequest):
    return await AddNewTV(add_request.name, add_request.season, add_request.torrent_url, add_request.regex_rule_episode, add_request.episode_offset, add_request.need_super_resolution, add_request.checked)

class TVDelRequest(BaseModel):
    tv_id: int
@app.post("/api/tv/del")
async def delete_tv(request: Request, del_request: TVDelRequest):
    return await DeleteTV(del_request.tv_id)

class MovieAddRequest(BaseModel):
    name: str
    torrent_url: str
    need_super_resolution: bool
    file_regex: str
    checked: bool
@app.post("/api/movie/add")
async def add_movie(request: Request, add_request: MovieAddRequest):
    return await AddNewMovie(add_request.name, add_request.torrent_url, add_request.need_super_resolution, add_request.file_regex, add_request.checked)

class MovieDelRequest(BaseModel):
    movie_id: int
@app.post("/api/movie/del")
async def delete_movie(request: Request, del_request: MovieDelRequest):
    return await DeleteMovie(del_request.movie_id)

class GetTrackList(BaseModel):
    track_type: str
    min_index: int
    count: int
@app.post("/api/track")
async def getTrack(request: Request, track_request: GetTrackList):
    with Session() as session:
        if track_request.min_index != -1:
            data = []
            if track_request.track_type == "bangumi":
                bangumis = session.query(Bangumi).order_by(Bangumi.id.desc()).offset(track_request.min_index).limit(track_request.count).all()
                data = [b.to_dict() for b in bangumis]
                for b in data:
                    b['status'] = await QueryBangumiStatus(b['id'])
            elif track_request.track_type == "tv":
                tvs = session.query(TV).order_by(TV.id.desc()).offset(track_request.min_index).limit(track_request.count).all()
                data = [t.to_dict() for t in tvs]
            elif track_request.track_type == "movie":
                movies = session.query(Movie).order_by(Movie.id.desc()).offset(track_request.min_index).limit(track_request.count).all()
                data = [m.to_dict() for m in movies]
            return JSONResponse(content=data)
        else:
            # Return count
            count = 0
            if track_request.track_type == "bangumi":
                count = session.query(Bangumi).filter().count()
            elif track_request.track_type == "tv":
                count = session.query(TV).filter().count()
            elif track_request.track_type == "movie":
                count = session.query(Movie).filter().count()
            return JSONResponse(content={"count": count})