from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, mapped_column, Mapped

from enum import Enum as PyEnum
from typing import List, Optional
from datetime import datetime

Base = declarative_base()

class TV(Base):
    __tablename__ = 'tv'
    id : Mapped[int] = mapped_column(primary_key=True)
    name : Mapped[str] = mapped_column()
    season : Mapped[str] = mapped_column()
    torrent_url : Mapped[str] = mapped_column()
    regex_rule_episode : Mapped[str] = mapped_column()
    episode_offset : Mapped[int] = mapped_column()
    need_super_resolution: Mapped[bool] = mapped_column()
    torrent : Mapped["Torrent"] = relationship(back_populates='tv', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'season': self.season,
            'torrent_url': self.torrent_url,
            'regex_rule_episode': self.regex_rule_episode,
            'need_super_resolution': self.need_super_resolution,
            'episode_offset': self.episode_offset
        }

class Movie(Base):
    __tablename__ = 'movie'
    id : Mapped[int] = mapped_column(primary_key=True)
    name : Mapped[str] = mapped_column()
    torrent_url : Mapped[str] = mapped_column()
    need_super_resolution: Mapped[bool] = mapped_column()
    torrent : Mapped["Torrent"] = relationship(back_populates='movie', cascade='all, delete-orphan')
    file_regex: Mapped[str] = mapped_column()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'torrent_url': self.torrent_url,
            'need_super_resolution': self.need_super_resolution
        }

class Bangumi(Base):
    __tablename__ = 'bangumi'
    id : Mapped[int] = mapped_column(primary_key=True)
    name : Mapped[str] = mapped_column()
    season : Mapped[str] = mapped_column()
    rss : Mapped[str] = mapped_column()
    regex_rule_episode : Mapped[str] = mapped_column()
    episode_offset : Mapped[int] = mapped_column()
    expire_time : Mapped[datetime] = mapped_column()
    last_update_time : Mapped[datetime] = mapped_column()
    need_super_resolution: Mapped[bool] = mapped_column()
    torrents : Mapped[List["Torrent"]] = relationship(back_populates='bangumi', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'season': self.season,
            'rss': self.rss,
            'regex_rule_episode': self.regex_rule_episode,
            'episode_offset': self.episode_offset,
            'need_super_resolution': self.need_super_resolution,
            'expire_time' : str(self.expire_time),
            'last_update_time' : str(self.last_update_time)
        }

class TorrentStatus(PyEnum):
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"

class TorrentType(PyEnum):
    MOVIE = "movie"
    TV = "tv"
    TV_SEASON = "tv_season"

class Torrent(Base):
    __tablename__ = "torrents"
    id : Mapped[int] = mapped_column(primary_key=True)
    status : Mapped[TorrentStatus] = mapped_column()
    torrent_type : Mapped[TorrentType] = mapped_column()
    episode_raw : Mapped[Optional[int]] = mapped_column()
    hash : Mapped[str] = mapped_column()
    magnet : Mapped[str] = mapped_column()

    bangumi_id : Mapped[Optional[int]] = mapped_column(ForeignKey('bangumi.id'))
    bangumi : Mapped[Optional[Bangumi]] = relationship(back_populates='torrents')

    tv_id : Mapped[Optional[int]] = mapped_column(ForeignKey('tv.id'))
    tv : Mapped[Optional[TV]] = relationship(back_populates='torrent')

    movie_id : Mapped[Optional[int]] = mapped_column(ForeignKey('movie.id'))
    movie : Mapped[Optional[Movie]] = relationship(back_populates='torrent')

    super_resolution_mission : Mapped[Optional["SRMission"]] = relationship(back_populates='torrent', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'status': self.status,
            'torrent_type': self.torrent_type,
            'episode_raw': self.episode_raw,
            'hash': self.hash
        }

class SRMissionStatus(PyEnum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    DONE = 'done'
    ERROR = 'error'

class SRMission(Base):
    __tablename__ = 'sr_mission'
    id : Mapped[int] = mapped_column(primary_key=True)
    input_file : Mapped[str] = mapped_column()
    output_file : Mapped[str] = mapped_column()
    status : Mapped[SRMissionStatus] = mapped_column()
    start_time : Mapped[datetime] = mapped_column(default=datetime.now)
    end_time : Mapped[datetime] = mapped_column(default=datetime.now)

    encode_duration_ms : Mapped[int] = mapped_column(default=0)
    super_resolution_duration_ms : Mapped[int] = mapped_column(default=0)
    progress_encode : Mapped[float] = mapped_column(default=0)
    progress_super_resolution : Mapped[float] = mapped_column(default=0)

    encoder : Mapped[str] = mapped_column()
    error_info : Mapped[str] = mapped_column(default='')

    torrent_id : Mapped[int] = mapped_column(ForeignKey('torrents.id'))
    torrent : Mapped[Torrent] = relationship(back_populates='super_resolution_mission')

    def to_dict(self):
        return {
            "id": self.id,
            "input_file": self.input_file,
            "output_file": self.output_file,
            "status": self.status.value,
            "start_time": str(self.start_time),
            "end_time": str(self.end_time),
            "encode_duration_ms": self.encode_duration_ms,
            "super_resolution_duration_ms": self.super_resolution_duration_ms,
            "progress_encode": self.progress_encode,
            "progress_super_resolution": self.progress_super_resolution,
            "encoder": self.encoder,
            "error_info": self.error_info
        }

engine = create_engine('sqlite:///database.sqlite')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)