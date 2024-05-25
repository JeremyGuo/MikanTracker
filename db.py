import sqlite3
from sqlalchemy import Column, Integer, String, create_engine, DateTime, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from enum import Enum as PyEnum
from typing import List, Optional
from datetime import datetime

### Main Table

# - id : NUMBER
# - name : TEXT
# - season : NUMBER
# - rss : TEXT
# - regex_rule_episode : TEXT
# - expire_time : DATE
# - last_udpate : DATE

### Proxy Table

# - id : NUMBER
# - name : TEXT
# - path : TEXT

### Torrents Table

# - id : NUMBER
# - status : NUMBER // Downloaded Ignored Waiting
# - main_id : NUMBER
# - episode : NUMBER
# - episode_infer : NUMBER
# - message_pushed : BOOLEAN

Base = declarative_base()

class TorrentStatus(PyEnum):
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"

class Bangumi(Base):
    __tablename__ = 'main_table'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    season = Column(Integer)
    rss = Column(String)
    regex_rule_episode = Column(String)
    expire_time = Column(DateTime)
    last_update_time = Column(DateTime)
    torrents = relationship('Magnet', back_populates='bangumi')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'regex_rule_episode': self.regex_rule_episode,
            'season': self.season,
            'torrents': [t.to_dict() for t in self.torrents],
            'rss': self.rss
        }

class Magnet(Base):
    __tablename__  = "torrents"
    id = Column(Integer, primary_key=True)
    status = Column(Enum(TorrentStatus))
    episode = Column(Integer)
    bangumi_id = Column(Integer, ForeignKey('main_table.id')) 
    bangumi = relationship('Bangumi', back_populates='torrents')
    hash = Column(String)

    def to_dict(self):
        return {
            'id': self.id,
            'episode': self.episode,
            'hash': self.hash
        }


engine = create_engine('sqlite:///db.sqlite')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
