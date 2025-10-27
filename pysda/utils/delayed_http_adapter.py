import time
from requests.adapters import HTTPAdapter
class SimpleLogger:
    @staticmethod
    def info(msg): print(f"[INFO] {msg}")
    @staticmethod
    def error(msg): print(f"[ERROR] {msg}")
    @staticmethod  
    def warning(msg): print(f"[WARNING] {msg}")
    @staticmethod
    def debug(msg): print(f"[DEBUG] {msg}")

logger = SimpleLogger()

class DelayedHTTPAdapter(HTTPAdapter):
    def __init__(self, *args, delay: float = 0, **kwargs):
        self.delay = delay
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        try:
            if 'timeout' not in kwargs or kwargs['timeout'] is None:
                kwargs['timeout'] = (10, 30)
            response = super().send(request, **kwargs)
            return response
        finally:
            if hasattr(self, 'delay') and self.delay > 0:
                logger.debug(f"Пауза на {self.delay:.2f} сек после запроса к {request.url}")
                time.sleep(self.delay) 
