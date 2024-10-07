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

    def to_dict(self):
        return {
            'id': self.id,
            'status': self.status,
            'torrent_type': self.torrent_type,
            'episode_raw': self.episode_raw,
            'hash': self.hash
        }

engine = create_engine('sqlite:///database.sqlite')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)