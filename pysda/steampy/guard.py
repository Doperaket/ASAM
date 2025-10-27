from __future__ import annotations

import hmac
import json
import struct
from base64 import b64decode, b64encode
from hashlib import sha1
from pathlib import Path
from time import time


def load_steam_guard(steam_guard: str) -> dict[str, str]:

    if Path(steam_guard).is_file():
        with Path(steam_guard).open() as f:
            return json.loads(f.read(), parse_int=str)
    else:
        return json.loads(steam_guard, parse_int=str)


def generate_one_time_code(shared_secret: str, timestamp: int | None = None) -> str:
    if timestamp is None:
        timestamp = int(time())
    time_buffer = struct.pack('>Q', timestamp // 30)
    time_hmac = hmac.new(b64decode(shared_secret), time_buffer, digestmod=sha1).digest()
    begin = ord(time_hmac[19:20]) & 0xF
    full_code = struct.unpack('>I', time_hmac[begin:begin + 4])[0] & 0x7FFFFFFF
    chars = '23456789BCDFGHJKMNPQRTVWXY'
    code = ''

    for _ in range(5):
        full_code, i = divmod(full_code, len(chars))
        code += chars[i]

    return code


def generate_confirmation_key(identity_secret: str, tag: str, timestamp: int = int(time())) -> bytes:
    buffer = struct.pack('>Q', timestamp) + tag.encode('ascii')
    return b64encode(hmac.new(b64decode(identity_secret), buffer, digestmod=sha1).digest())


def generate_device_id(steam_id: str) -> str:
    hexed_steam_id = sha1(steam_id.encode('ascii')).hexdigest()
    return 'android:' + '-'.join((
        hexed_steam_id[:8],
        hexed_steam_id[8:12],
        hexed_steam_id[12:16],
        hexed_steam_id[16:20],
        hexed_steam_id[20:32],
    ))

