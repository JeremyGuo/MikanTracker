#!/usr/bin/python

# xxx.py "%F" "%I"
import sys
import urllib.request
import urllib.parse

finish_api = "http://192.168.1.169:8000/api/finish"
torrent_path = sys.argv[1]
torrent_hash = sys.argv[2]
mounted_root = '/Shared/'

if not torrent_path.startswith(mounted_root):
    raise Exception('Not in mounted root')
torrent_path = torrent_path[len(mounted_root):]

import json
data = json.dumps({'hash': torrent_hash, 'path': torrent_path}).encode('utf-8')
headers = {'Content-Type': 'application/json'}
opener = urllib.request.build_opener()
request = urllib.request.Request(finish_api, data=data, headers=headers, method='POST')
response = opener.open(request)
print(response)
