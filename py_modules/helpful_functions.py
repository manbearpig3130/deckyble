import decky_plugin
from struct import *
import socket, sys, time, datetime, numpy, json
from dataclasses import dataclass, asdict

@dataclass
class ServerConnection:
    host: str
    port: int
    username: str
    password: str
    label: str

    def to_json(self):
        return asdict(self)
    
    @classmethod
    def from_json(cls, json_string):
        data = json.loads(json_string)
        return cls(**data)

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

def mono_to_stereo(data, channels=2):
        mono_audio_data = numpy.frombuffer(data, dtype=numpy.int16)  # Convert the data to a NumPy array
        stereo_array = numpy.vstack((mono_audio_data, mono_audio_data)).T
        return numpy.ascontiguousarray(stereo_array)

## This helps to catch errors in functions without having to wrap every function in a try/except block
def catch_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            decky_plugin.logger.error(f"Error in {func.__name__}: {e}")
    return wrapper
