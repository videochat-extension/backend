import requests
import time
import random
import socket
import sys
import struct

ip = socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))
try:
    r = requests.get(f'https://ve-api.starbase.wiki/geo?ip={ip}&lang=en')
except Exception as E:
    sys.exit(str(E))
if r.status_code == 200:
    sys.exit()
else:
    sys.exit(r.status_code)
