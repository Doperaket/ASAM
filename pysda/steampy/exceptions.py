from .models import EResult
class SteamError(Exception):

class EResultError(SteamError):

    def __init__(self, msg: str, result: EResult, data=None):
        self.msg = msg
        self.result = result
        self.data = data

class SevenDaysHoldException(Exception):
    pass


class TooManyRequests(Exception):
    pass


class ApiException(Exception):
    pass


class LoginRequired(Exception):
    pass


class InvalidCredentials(Exception):
    pass


class CaptchaRequired(Exception):
    pass


class ConfirmationExpected(Exception):
    pass


class ProxyConnectionError(Exception):
    pass

