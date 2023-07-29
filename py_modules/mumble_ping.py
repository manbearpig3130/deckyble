# mumble_ping.py

from struct import *
from string import Template
import socket, sys, time, datetime

def mumble_ping(host, port, verbose=False):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(1)

    buf = pack(">iQ", 0, datetime.datetime.now().microsecond)
    s.sendto(buf, (host, port))

    try:
        data, _ = s.recvfrom(1024)
    except socket.timeout:
        print(f"{time.time()}:NaN:NaN")
        sys.exit()

    r = unpack(">bbbbQiii", data)

    ping = (datetime.datetime.now().microsecond - r[4]) / 1000.0
    if ping < 0:
        ping = ping + 1000

    return {
        'version': '.'.join([str(v) for v in r[1:4]]),
        'users': r[5],
        'max_users': r[6],
        'ping': int(ping),
        'bandwidth': f"{r[7] / 1000}kbit/s",
    }