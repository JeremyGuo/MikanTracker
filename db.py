import sqlite3
from sqlalchemy import Integer, String, create_engine, DateTime, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, mapped_column, Mapped
from enum import Enum as PyEnum
from typing import List, Optional
from datetime import datetime

Base = declarative_base()

class Bangumi(Base):
    __tablename__ = 'main_table'
    id : Mapped[int] = mapped_column(primary_key=True)
    name : Mapped[str] = mapped_column()
    season : Mapped[str] = mapped_column()
    rss : Mapped[str] = mapped_column()
    regex_rule_episode : Mapped[str] = mapped_column()
    expire_time : Mapped[datetime] = mapped_column()
    last_update_time : Mapped[datetime] = mapped_column()
    torrents : Mapped[List["Magnet"]] = relationship('Magnet', back_populates='bangumi', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'regex_rule_episode': self.regex_rule_episode,
            'season': self.season,
            'torrents': [t.to_dict() for t in self.torrents],
            'rss': self.rss
        }

class TorrentStatus(PyEnum):
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"

class Magnet(Base):
    __tablename__  = "torrents"
    id : Mapped[int] = mapped_column(primary_key=True)
    status : Mapped[TorrentStatus] = mapped_column()
    episode : Mapped[int] = mapped_column()
    bangumi_id : Mapped[int] = mapped_column(ForeignKey('main_table.id'))
    bangumi : Mapped["Bangumi"] = relationship(back_populates='torrents')
    hash : Mapped[str] = mapped_column()

    def to_dict(self):
        return {
            'id': self.id,
            'episode': self.episode,
            'hash': self.hash
        }

engine = create_engine('sqlite:///db.sqlite')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
