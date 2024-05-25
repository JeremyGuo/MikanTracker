# 自动下载追番工具

## 写在前面

本工具非常简单，主要用于监听并实时下载番剧。

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
