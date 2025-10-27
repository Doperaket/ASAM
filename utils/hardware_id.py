import hashlib
import uuid
import platform

def get_hardware_id() -> str:
    system = platform.system()
    node = platform.node()
    release = platform.release()
    version = platform.version()
    machine = platform.machine()
    processor = platform.processor()
    mac = uuid.getnode()
    raw = f"{system}-{release}-{machine}-{processor}-{mac}"
    hwid = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    return hwid

if __name__ == "__main__":
    print("Ваш HWID:", get_hardware_id())