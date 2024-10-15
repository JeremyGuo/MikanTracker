import requests
import config
import json
from model import Torrent, Session, TorrentType
from log import log

req_session = requests.Session()

# If a post is 5min old, re-post login
login_data = {
    'username': config.qbittorrent_username,
    'password': config.qbittorrent_password
}
response = req_session.post(f'{config.qbittorrent_url}/api/v2/auth/login', data=login_data)
if response.text != 'Ok.':
    raise Exception('登录失败，请检查用户名和密码')
import datetime
last_login_date = datetime.datetime.now()
def CheckLogin():
    if (datetime.datetime.now() - last_login_date).seconds > 300:
        response = req_session.post(f'{config.qbittorrent_url}/api/v2/auth/login', data=login_data)
        if response.text != 'Ok.':
            raise Exception('登录失败，请检查用户名和密码')

def AddTorrent(torrent_id: int):
    CheckLogin()
    with Session() as session:
        torrent = session.query(Torrent).filter_by(id=torrent_id).first()
        if torrent == None:
            raise Exception(f'添加种子失败：找不到种子 {torrent_id}')
        status, rate = GetTorrentStatus(torrent.hash)
        if status != "Not Added":
            raise Exception(f'添加种子失败：种子已经添加 {torrent.hash}')
        tags = ''
        category = ''
        if torrent.torrent_type == TorrentType.TV_SEASON:
            tags = f'Ep:{torrent.episode_raw + torrent.bangumi.episode_offset},Name:{torrent.bangumi.name},Season:{torrent.bangumi.season}'
            category = 'TV-Season'
        elif torrent.torrent_type == TorrentType.MOVIE:
            tags = f'Name:{torrent.movie.name}'
            category = 'Movie'
        elif torrent.torrent_type == TorrentType.TV:
            tags = f'Name:{torrent.tv.name},Season:{torrent.tv.season}'
            category = 'TV'
        torrent_data = {
            'urls': torrent.magnet,
            'tags': tags,
            'category': category
        }
        response = req_session.post(f'{config.qbittorrent_url}/api/v2/torrents/add', data=torrent_data)
        if response.status_code != 200 or response.text != 'Ok.':
            raise Exception(f'添加种子失败 {response.text} {response.status_code} {torrent_data}')

def GetTorrentPath(hash) -> str:
    CheckLogin()
    torrent_data = {
        'hashes': hash
    }
    try:
        response = req_session.post(f'{config.qbittorrent_url}/api/v2/torrents/info', data=torrent_data)
        if response.status_code != 200:
            return None
        data = json.loads(response.text)
        return data[0]['content_path']
    except Exception as e:
        log(str(e))
        return None

def GetTorrentStatus(hash):
    CheckLogin()
    torrent_data = {
        'hashes': hash
    }
    response = req_session.post(f'{config.qbittorrent_url}/api/v2/torrents/info', data=torrent_data)
    if response.status_code != 200:
        return "Unknown", 0
    data = json.loads(response.text)
    if len(data) == 0:
        return "Not Added", 0
    return str(data[0]['progress'] * 100) + '%', data[0]['progress']