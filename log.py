# 1. Open the log file corresponding to the current date
# 2. Write the log to the file and flush immediately (consider the asyncio access from different thread)
# 3. Close the file after writing

import os
import datetime

log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_file = os.path.join(log_dir, f"{datetime.datetime.now().strftime('%Y-%m-%d')}.log")
f = open(log_file, "a")

def log(msg):
    print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}")
    f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    f.flush()