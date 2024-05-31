# 自动下载追番工具

## 写在前面

本工具非常简单，主要用于监听并实时下载番剧。

**注意** 系统不带任何加密，自己内网用的，担心被其他人看到的可以帮我加一个，或者自己改改（手动狗头

一个番剧被认为具有如下属性：

1. 名字
2. 季
3. RSS源头
4. 用于提取集数的正则表达式

主要实现如下的工作流：

1. 实时监听RSS源
2. 当RSS源更新，利用正则表达式提取集数，然后tags设置为"Name:名字,Season:季,Ep:集数"，category设置为"TV-Season"，然后提交到qBittorrent下载
3. 当qBittorrent下载完成后，通过Telegram Bot进行通知

## 快速部署

**注意** 硬链接+通知 和 自动下载是解耦的，硬链接+通知是为qBittorrent开发的功能，自动下载是本系统的主要功能。qBittorrent和本系统可以不在同一台机器中。

### 自动下载

1. 安装依赖项：`pip install -r requirements.txt`
2. 复制config.template.py到config.py并填写设置
3. `python3 main.py`运行
4. 打开浏览器，访问`http://IP:8000`即可使用

### qBittorrent硬链接+通知

脚本的作用是帮我建立硬链接，并移动到 番剧名/Season/番剧名 S[]E[].xxx的位置上，方便自动刮削。

这个不是这个的重点，大家随便搞搞就好

1. 填写scripts_for_qb/downloaded.py中的设置，然后拷贝到qBittorrent服务器所在目录下
2. 设置下载完成后执行`script.py "%N" "%F" "%L" "%G"`（硬链接+通知）
