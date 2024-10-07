proxies = { # SOCKS5代理
    'http': 'http://127.0.0.1:20172',
    'https': 'http://127.0.0.1:20172',
}

# 配置qBittorrent Web UI的URL和认证信息
qbittorrent_url = 'http://192.168.1.213:8080'   # 请根据实际情况修改
qbittorrent_username = ''                       # 请根据实际情况修改
qbittorrent_password = ''                       # 请根据实际情况修改

mounted_path = "/mnt/data"                      # 存放数据的根目录
tv_save_path = mounted_path + "/Video"          # 实际存放的子目录，这里实际上会存放到/mnt/data/Video/TV_NAME/SEASON/EPISODE.mp4/mkv...
movie_save_path = mounted_path + "/Video"       # 实际存放的子目录，这里实际上会存放到/mnt/data/Video/MOVIE_NAME.mp4/mkv...
bangumi_save_path = mounted_path + "/Video"     # 实际存放的子目录，这里实际上会存放到/mnt/data/Video/BANGUMI_NAME/SEASON/EPISODE.mp4/mkv...

notifications = {
    'telegram': {
        'type': '',
        'token': '',
        'chat_id': ''
    }
}

enable_super_resolution = False                 # 是否启用超分辨率