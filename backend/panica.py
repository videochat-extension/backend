import requests
import time
import sys
import faker


from faker import Faker
fake = Faker()

ip = fake.ipv4_public()
try:
    r = requests.get(f'https://ve-api.starbase.wiki/geo?ip={ip}&lang=en')
except Exception as E:
    sys.exit(str(E))
if r.status_code == 200:
    sys.exit()
else:
    sys.exit(r.status_code)
