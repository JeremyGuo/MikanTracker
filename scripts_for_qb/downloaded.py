#!/usr/bin/python
from genericpath import isfile
import os
import re
import sys
import shutil
import urllib.request
import urllib.parse

BOT_TOKEN = ''  # BOT_TOKEN of telegram
CHAT_ID = ''    # CHAT_ID of telegram channel
PROXY = None # PROXY = {'http': 'http://123', 'https': 'http://123'} Optional proxy
target_path = "/Shared/Video_Unclassified"  # Target path for TV & Movie & Others
season_root_path = "/Shared/Video"          # Target path for TV-Season to save

def send_telegram_message(text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = urllib.parse.urlencode({'chat_id': CHAT_ID, 'text': text}).encode('utf-8')
    opener = None
    if PROXY != None:
        proxy_handler = urllib.request.ProxyHandler(PROXY)
        opener = urllib.request.build_opener(proxy_handler)
    else:
        opener = urllib.request.build_opener()
    request = urllib.request.Request(url, data=data)
    response = opener.open(request)

if len(sys.argv) < 4:
    exit(0)

torrent_name = sys.argv[1]
torrent_path = sys.argv[2]
torrent_category = sys.argv[3]

tags = [] # "Name:XXX, Season:XXX, Ep:XXX"
season_id = 0
season_epid = 0
season_name = ""
season_current_path = ""
is_season = False
if len(sys.argv) > 4:
    is_season = True
    tags = sys.argv[4].split(',')
    for tag_ in tags:
        tag = tag_.strip()
        if tag.startswith("Name:"):
            season_name = tag[5:].strip()
        if tag.startswith("Season:"):
            season_id = int(tag[7:].strip())
        if tag.startswith("Ep:"):
            season_epid = int(tag[3:].strip())
    
    if season_name == "" or season_id == 0 or  season_epid == 0:
        is_season = False

link_path_directory = os.path.join(target_path, torrent_category, torrent_name)
link_path_file_dir = os.path.join(target_path, torrent_category)
link_path_file = os.path.join(target_path, torrent_category, torrent_name)

def is_video_file(filename):
    video_extensions = (".mp4", ".avi", ".mkv", ".rmvb", ".mov", ".rm", ".mpeg", ".ass")
    return filename.endswith(video_extensions)

def rename_video_file(filename, new_name, sid, epid):
    file_extension = os.path.splitext(filename)[1]
    new_filename = f"{new_name} S{str(sid).zfill(2)}E{str(epid).zfill(2)}{file_extension}"
    return new_filename
    

if torrent_category in ["Movie", "TV", "Others"]:
    if os.path.isdir(torrent_path):
        os.makedirs(link_path_directory, exist_ok=True)
        for root, _, files in os.walk(torrent_path):
            for filename in files:
                if is_video_file(filename):
                    src_path = os.path.join(root, filename)
                    dest_dir = os.path.relpath(root, torrent_path)
                    dest_path = os.path.join(link_path_directory, dest_dir, filename)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    os.link(src_path, dest_path)  # 创建硬链接
    elif os.path.isfile(torrent_path):
        os.makedirs(link_path_file_dir, exist_ok=True)
        os.link(torrent_path, link_path_file)  # 创建硬链接

if torrent_category in ["TV-Season"] and is_season:
    target_dir = os.path.join(season_root_path, season_name, f"Season {season_id}")
    os.makedirs(target_dir, exist_ok=True)
    if os.path.isdir(torrent_path):
        for root, _, files in os.walk(torrent_path):
            for filename in files:
                if is_video_file(filename):
                    src_path = os.path.join(root, filename)
                    dst_path = os.path.join(target_dir, rename_video_file(filename, season_name, season_id, season_epid))
                    os.link(src_path, dst_path)  # 创建硬链接
    elif os.path.isfile(torrent_path) and is_video_file(torrent_path):
        src_path = torrent_path
        filename = os.path.basename(torrent_path)
        dst_path = os.path.join(target_dir, rename_video_file(filename, season_name, season_id, season_epid))
        os.link(src_path, dst_path)
    
    send_telegram_message(f'Download completed: {season_name} Season {season_id} Episode {season_epid}')