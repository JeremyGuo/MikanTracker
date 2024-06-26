import requests
import config
import json

session = requests.Session()

# If a post is 5min old, re-post login
login_data = {
    'username': config.qbittorrent_username,
    'password': config.qbittorrent_password
}
response = session.post(f'{config.qbittorrent_url}/api/v2/auth/login', data=login_data)
if response.text != 'Ok.':
    raise Exception('登录失败，请检查用户名和密码')
print('QB 登陆成功')
import datetime
last_login_date = datetime.datetime.now()
def CheckLogin():
    if (datetime.datetime.now() - last_login_date).seconds > 300:
        response = session.post(f'{config.qbittorrent_url}/api/v2/auth/login', data=login_data)
        if response.text != 'Ok.':
            raise Exception('登录失败，请检查用户名和密码')
        print('QB 登陆成功')

def AddTorrent(url, tags, hash):
    CheckLogin()
    response = None
    retry_count = 5

    while retry_count > 0 and response == None:
        torrent_data = { 'hashes': hash }
        retry_count -= 1
        response = session.post(f'{config.qbittorrent_url}/api/v2/torrents/info', data=torrent_data)
        if response.status_code != 200:
            response = None
    
    if response == None:
        raise Exception(f'添加种子失败：查询失败 {response.status_code}')
    
    if len(json.loads(response.text)) > 0:
        print("种子已经在qBittorrent下载列表中")
        return
    
    torrent_data = {
        'urls': url,
        'tags': tags,
        'category': 'TV-Season'
    }
    response = session.post(f'{config.qbittorrent_url}/api/v2/torrents/add', data=torrent_data)
    if response.status_code != 200 or response.text != 'Ok.':
        raise Exception(f'添加种子失败 {response.text} {response.status_code} {torrent_data}')

def GetTorrentStatus(hash):
    CheckLogin()
    torrent_data = {
        'hashes': hash
    }
    response = session.post(f'{config.qbittorrent_url}/api/v2/torrents/info', data=torrent_data)
    if response.status_code != 200:
        return "Unknown"
    data = json.loads(response.text)
    if len(data) == 0:
        return "Not Added"
    return str(data[0]['progress'] * 100) + '%'