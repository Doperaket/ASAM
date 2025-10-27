import base64
import hmac
import struct
import time
from datetime import datetime

from colorama import init, Fore

init(autoreset=True)


def clean_base64(data):
    if not data:
        return ""
    
    cleaned = data.replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "")
    
    missing_padding = len(cleaned) % 4
    if missing_padding:
        cleaned += '=' * (4 - missing_padding)
    
    return cleaned


def generate_2fa(shared_secret, debug=True):
    try:
        if not shared_secret:
            raise ValueError("shared_secret is empty")

        clean_secret = clean_base64(shared_secret)
        if not clean_secret:
            raise ValueError("shared_secret is empty after cleaning")

        try:
            key = base64.b64decode(clean_secret, validate=True)
        except Exception as e:
            try:
                key = base64.b64decode(clean_secret)
            except Exception as e2:
                raise ValueError(f"Invalid Base64 in shared_secret: {e}. Fallback also failed: {e2}")

        timestamp = int(time.time())
        if debug:
            print(f"{Fore.BLUE}[DEBUG] Timestamp: {timestamp} ({datetime.fromtimestamp(timestamp)})")

        time_buffer = struct.pack('>Q', timestamp // 30)

        hmac_hash = hmac.new(key, time_buffer, 'sha1').digest()
        if debug:
            print(f"{Fore.BLUE}[DEBUG] HMAC hash: {hmac_hash.hex()}")

        offset = hmac_hash[-1] & 0x0F
        if debug:
            print(f"{Fore.BLUE}[DEBUG] Offset: {offset}")

        code = struct.unpack('>I', hmac_hash[offset:offset + 4])[0] & 0x7FFFFFFF
        if debug:
            print(f"{Fore.BLUE}[DEBUG] Raw code: {code}")

        steam_chars = '23456789BCDFGHJKMNPQRTVWXY'

        final_code = ''
        for _ in range(5):
            code, remainder = divmod(code, len(steam_chars))
            final_code += steam_chars[remainder]

        if debug:
            print(f"{Fore.BLUE}[DEBUG] Final 2FA code: {final_code}")
        return final_code

    except Exception as e:
        if debug:
            print(f"{Fore.RED}❌ Ошибка в generate_2fa: {e}")
        raise


def generate_2fa_code(mafile_path):
    try:
        import json
        
        with open(mafile_path, 'r', encoding='utf-8') as f:
            mafile_data = json.load(f)
        
        shared_secret = mafile_data.get('shared_secret')
        if not shared_secret:
            return None, 0
        
        code = generate_2fa(shared_secret, debug=False)
        
        current_time = int(time.time())
        time_remaining = 30 - (current_time % 30)
        
        return code, time_remaining
        
    except Exception as e:
        print(f"Ошибка в generate_2fa_code: {e}")
        return None, 0



