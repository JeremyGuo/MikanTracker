import config
import urllib.request

def sendNotificationFinish(type:str, name:str, done_what:str, at_where:str):
    for key in config.notifications:
        v = config.notifications[key]
        if v['type'] == 'telegram':
            if 'token' in v and 'chat_id' in v:
                try:
                    text = f"Download {type} {name} finishes to {done_what} at {at_where}"
                    url = f'https://api.telegram.org/bot{v["token"]}/sendMessage'
                    data = urllib.parse.urlencode({'chat_id': v["chat_id"], 'text': text}).encode('utf-8')
                    opener = None
                    if config.proxies != None:
                        proxy_handler = urllib.request.ProxyHandler(config.proxies)
                        opener = urllib.request.build_opener(proxy_handler)
                    else:
                        opener = urllib.request.build_opener()
                    request = urllib.request.Request(url, data=data)
                    response = opener.open(request)
                except Exception as e:
                    print(e)

def sendNotificationWarning():
    pass

def sendNotificationError():
    pass