import decky_plugin
from struct import *
import socket, sys, time, datetime, numpy, json
from dataclasses import dataclass, asdict
from typing import Optional, List

@dataclass
class ServerConnection:
    host: str
    port: int
    username: str
    password: str
    label: str
    tokens: Optional[List[str]] = None

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
    
    try:
        s.sendto(buf, (host, port))
        data, _ = s.recvfrom(1024)
    except socket.timeout:
        decky_plugin.logger.info(f"{host} timed out")
        return {
            'version': '',
            'users': '',
            'max_users': '',
            'ping': '',
            'bandwidth': ''}
    except Exception as e:
        decky_plugin.logger.info(f"Farted: {e}")
        return {
            'version': '',
            'users': '',
            'max_users': '',
            'ping': '',
            'bandwidth': ''}

    r = unpack(">bbbbQiii", data)
    #decky_plugin.logger.info(f"Received ping response: {r}")

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


def phase_correlation(x, y):
    # Compute the FFT of the audio data
    X = numpy.fft.fft(x)
    Y = numpy.fft.fft(y)

    # Compute the cross-power spectrum
    R = X * numpy.conj(Y)

    # Compute the phase correlation function
    r = numpy.fft.ifft(R / numpy.abs(R))

    # Find the peak of the phase correlation function
    peak = numpy.argmax(numpy.abs(r))

    # Compute the phase difference between the two signals
    phase_diff = numpy.angle(R[peak])

    return phase_diff

def limiter(x, threshold):
    # Compute the maximum absolute value of the audio data
    max_val = numpy.max(numpy.abs(x))

    # If the maximum value exceeds the threshold, scale the audio data
    if max_val > threshold:
        x = x * threshold / max_val

    return x


def power_mixing(audio_data, vol):
    # Compute the power of the audio data
    power = numpy.mean(numpy.abs(audio_data) ** 2)

    # Compute the scaling factor based on the power
    scale = numpy.sqrt(1 / power)

    # Scale the audio data based on the volume and power
    audio_data = audio_data * vol * scale

    return audio_data