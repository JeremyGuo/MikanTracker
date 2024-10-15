#!/usr/bin/python

# xxx.py "%I"
import sys
import urllib.request
import urllib.parse

finish_api = "http://192.168.1.169:8000/api/finish"
torrent_hash = sys.argv[1]

import json
data = json.dumps({'hash': torrent_hash}).encode('utf-8')
headers = {'Content-Type': 'application/json'}
opener = urllib.request.build_opener()
request = urllib.request.Request(finish_api, data=data, headers=headers, method='POST')
response = opener.open(request)
print(response)
