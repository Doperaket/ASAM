class DummyLogger:
    def info(self, *args, **kwargs):
        pass
    def warning(self, *args, **kwargs):
        pass
    def error(self, *args, **kwargs):
        pass
    def success(self, *args, **kwargs):
        pass
    def debug(self, *args, **kwargs):
        pass
    def remove(self, *args, **kwargs):
        pass

logger = DummyLogger()

def print_and_log(message: str, level: str = "INFO"):
    print(message)
