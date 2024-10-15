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

# 以下为超分辨率RealCUGAN的配置，详见RealCUGAN-Tensor仓库
from pathlib import Path
sr_num_thread = 2                     
sr_scale = 2
sr_model_name = 'pro-conservative-up2x.pth'
sr_model_path = Path(__file__).parent / f"third_party/realCUGAN/Real-CUGAN/weights_v3/{sr_model_name}"
sr_half = True
sr_tile = 5
sr_cache_mode = 0
sr_alpha = 1
sr_tmp_dir = Path.home() / "tmp"
sr_encode_params = ['-crf', '21']
sr_device = "cuda:0"
