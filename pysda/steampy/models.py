try:
    from enum import IntEnum, Enum
except ImportError:
    class IntEnum:
        pass
    class Enum:
        pass
        
from typing import NamedTuple


class PredefinedOptions(NamedTuple):
    app_id: str
    context_id: str

class GameOptions:
    STEAM = PredefinedOptions('753', '6')
    DOTA2 = PredefinedOptions('570', '2')
    CS = PredefinedOptions('730', '2')
    TF2 = PredefinedOptions('440', '2')
    PUBG = PredefinedOptions('578080', '2')
    RUST = PredefinedOptions('252490', '2')

    def __init__(self, app_id: str, context_id: str) -> None:
        self.app_id = app_id
        self.context_id = context_id


class Asset:
    def __init__(self, asset_id: str, game: GameOptions, amount: int = 1) -> None:
        self.asset_id = asset_id
        self.game = game
        self.amount = amount

    def to_dict(self) -> dict:
        return {
            'appid': int(self.game.app_id),
            'contextid': self.game.context_id,
            'amount': self.amount,
            'assetid': self.asset_id,
        }


class Currency(IntEnum):
    USD = 1
    GBP = 2
    EURO = 3
    CHF = 4
    RUB = 5
    PLN = 6
    BRL = 7
    JPY = 8
    NOK = 9
    IDR = 10
    MYR = 11
    PHP = 12
    SGD = 13
    THB = 14
    VND = 15
    KRW = 16
    TRY = 17
    UAH = 18
    MXN = 19
    CAD = 20
    AUD = 21
    NZD = 22
    CNY = 23
    INR = 24
    CLP = 25
    PEN = 26
    COP = 27
    ZAR = 28
    HKD = 29
    TWD = 30
    SAR = 31
    AED = 32
    SEK = 33
    ARS = 34
    ILS = 35
    BYN = 36
    KZT = 37
    KWD = 38
    QAR = 39
    CRC = 40
    UYU = 41
    BGN = 42
    HRK = 43
    CZK = 44
    DKK = 45
    HUF = 46
    RON = 47


class TradeOfferState(IntEnum):
    Invalid = 1
    Active = 2
    Accepted = 3
    Countered = 4
    Expired = 5
    Canceled = 6
    Declined = 7
    InvalidItems = 8
    CreatedNeedsConfirmation = 9
    CanceledBySecondFactor = 10
    InEscrow = 11

class EResult:
    OK = 1
    AccessDenied = 5

class SteamUrl:
    API_URL = 'https://api.steampowered.com'
    COMMUNITY_URL = 'https://steamcommunity.com'
    STORE_URL = 'https://store.steampowered.com'
    LOGIN_URL = 'https://login.steampowered.com'


class Endpoints:
    CHAT_LOGIN = f'{SteamUrl.API_URL}/ISteamWebUserPresenceOAuth/Logon/v1'
    SEND_MESSAGE = f'{SteamUrl.API_URL}/ISteamWebUserPresenceOAuth/Message/v1'
    CHAT_LOGOUT = f'{SteamUrl.API_URL}/ISteamWebUserPresenceOAuth/Logoff/v1'
    CHAT_POLL = f'{SteamUrl.API_URL}/ISteamWebUserPresenceOAuth/Poll/v1'



from typing import TypeAlias, Any, TypeVar, Coroutine, Mapping

from yarl import URL

try:
    from aenum import extend_enum
except ImportError:
    def extend_enum(enum_class, name, value):
        setattr(enum_class, name, value)

_T = TypeVar("_T")

CORO: TypeAlias = Coroutine[Any, Any, _T]


class App(IntEnum):

    CS2 = 730
    CSGO = CS2

    DOTA2 = 570
    H1Z1 = 433850
    RUST = 252490
    TF2 = 440
    PUBG = 578080

    STEAM = 753

    @classmethod
    def _missing_(cls, value: int):
        return extend_enum(cls, cls._generate_name(value), value)

    @classmethod
    def _generate_name(cls, value) -> str:
        return f"{cls.__name__}_{value}"

    @property
    def app_id(self) -> int:
        return self.value


class AppContext(Enum):


    CS2 = App.CS2, 2
    CSGO = CS2

    DOTA2 = App.DOTA2, 2
    H1Z1 = App.H1Z1, 2
    RUST = App.RUST, 2
    TF2 = App.TF2, 2
    PUBG = App.PUBG, 2

    STEAM_GIFTS = App.STEAM, 1
    STEAM_COMMUNITY = App.STEAM, 6
    STEAM_REWARDS = App.STEAM, 7

    @classmethod
    def _generate_name(cls, value: tuple[App, int]) -> str:
        return f"{cls.__name__}_{value[0]}_{value[1]}"

    @classmethod
    def _missing_(cls, value: tuple[App | int, int]):
        with_enum = (App(value[0]), value[1])
        return extend_enum(cls, cls._generate_name(with_enum), with_enum)

    @property
    def app(self) -> App:
        return self.value[0]

    @property
    def app_id(self) -> int:
        return self.value[0].value

    @property
    def context(self) -> int:
        return self.value[1]


class Currency(IntEnum):


    USD = 1
    GBP = 2
    EUR = 3
    CHF = 4
    RUB = 5
    PLN = 6
    BRL = 7
    JPY = 8
    NOK = 9
    IDR = 10
    MYR = 11
    PHP = 12
    SGD = 13
    THB = 14
    VND = 15
    KRW = 16
    TRY = 17
    UAH = 18
    MXN = 19
    CAD = 20
    AUD = 21
    NZD = 22
    CNY = 23
    INR = 24
    CLP = 25
    PEN = 26
    COP = 27
    ZAR = 28
    HKD = 29
    TWD = 30
    SAR = 31
    AED = 32
    ARS = 34
    ILS = 35
    KZT = 37
    KWD = 38
    QAR = 39
    CRC = 40
    UYU = 41


class Language(str, Enum):


    ARABIC = "arabic"
    BULGARIAN = "bulgarian"
    SIMPLIFIED_CHINESE = "schinese"
    TRADITIONAL_CHINESE = "tchinese"
    CZECH = "czech"
    DANISH = "danish"
    DUTCH = "dutch"
    ENGLISH = "english"
    FINNISH = "finnish"
    FRENCH = "french"
    GERMAN = "german"
    GREEK = "greek"
    HUNGARIAN = "hungarian"
    ITALIAN = "italian"
    JAPANESE = "japanese"
    KOREAN = "koreana"
    NORWEGIAN = "norwegian"
    POLISH = "polish"
    PORTUGUESE = "portuguese"
    PORTUGUESE_BRAZIL = "brazilian"
    ROMANIAN = "romanian"
    RUSSIAN = "russian"
    SPANISH = "spanish"
    SPANISH_LATIN_AMERICAN = "latam"
    SWEDISH = "swedish"
    THAI = "thai"
    TURKISH = "turkish"
    UKRAINIAN = "ukrainian"
    VIETNAMESE = "vietnamese"

    def __str__(self):
        return self.value


class TradeOfferStatus(Enum):
    INVALID = 1
    ACTIVE = 2
    ACCEPTED = 3
    COUNTERED = 4
    EXPIRED = 5
    CANCELED = 6
    DECLINED = 7
    INVALID_ITEMS = 8
    CREATED_NEEDS_CONFIRMATION = 9
    CANCELED_BY_SECOND_FACTOR = 10
    IN_ESCROW = 11


class ConfirmationType(Enum):
    UNKNOWN = 1
    TRADE = 2
    LISTING = 3
    API_KEY = 4

    @classmethod
    def get(cls, v: int) -> "ConfirmationType":
        try:
            return cls(v)
        except ValueError:
            return cls.UNKNOWN


class MarketListingStatus(Enum):
    NEED_CONFIRMATION = 17
    ACTIVE = 1


class MarketHistoryEventType(Enum):
    LISTING_CREATED = 1
    LISTING_CANCELED = 2
    LISTING_SOLD = 3
    LISTING_PURCHASED = 4


_API_BASE = URL("https://api.steampowered.com")
_v = "v1"


class STEAM_URL:
    COMMUNITY = URL("https://steamcommunity.com")
    STORE = URL("https://store.steampowered.com")
    LOGIN = URL("https://login.steampowered.com")
    HELP = URL("https://help.steampowered.com")
    STATIC = URL("https://community.akamai.steamstatic.com")
    MARKET = COMMUNITY / "market/"
    TRADE = COMMUNITY / "tradeoffer"

    class API:
        BASE = _API_BASE

        class IEconService:
            _Base = _API_BASE / "IEconService"

            GetTradeHistory = _Base / "GetTradeHistory" / _v
            GetTradeHoldDurations = _Base / "GetTradeHoldDurations" / _v
            GetTradeOffer = _Base / "GetTradeOffer" / _v
            GetTradeOffers = _Base / "GetTradeOffers" / _v
            GetTradeOffersSummary = _Base / "GetTradeOffersSummary" / _v
            GetTradeStatus = _Base / "GetTradeStatus" / _v

        class IAuthService:
            _Base = _API_BASE / "IAuthenticationService"

            BeginAuthSessionViaCredentials = _Base / "BeginAuthSessionViaCredentials" / _v
            GetPasswordRSAPublicKey = _Base / "GetPasswordRSAPublicKey" / _v
            UpdateAuthSessionWithSteamGuardCode = _Base / "UpdateAuthSessionWithSteamGuardCode" / _v
            PollAuthSessionStatus = _Base / "PollAuthSessionStatus" / _v
            GenerateAccessTokenForApp = _Base / "GenerateAccessTokenForApp" / _v


T_PARAMS: TypeAlias = Mapping[str, int | str | float]
T_PAYLOAD: TypeAlias = Mapping[str, str | int | float | bool | None | list | Mapping]
T_HEADERS: TypeAlias = Mapping[str, str]


class EnumWithMultipleValues(Enum):

    def __new__(cls, *values):
        obj = object.__new__(cls)
        obj._value_ = values[0]
        if not hasattr(cls, "_alt_map"):
            cls._alt_map = {}
        for value in values:
            cls._alt_map[value] = obj
        return obj

    @classmethod
    def _missing_(cls, value):
        return cls._alt_map.get(value, super()._missing_(value))


class TransferResult:
    OK = 1
    AccessDenied = 5


class EResult(EnumWithMultipleValues):


    UNKNOWN = None

    INVALID = 0
    OK = 1, True
    FAIL = 2
    NO_CONNECTION = 3
    INVALID_PASSWORD = 5
    LOGGED_IN_ELSEWHERE = 6
    INVALID_PROTOCOL_VER = 7
    INVALID_PARAM = 8
    FILE_NOT_FOUND = 9
    BUSY = 10
    INVALID_STATE = 11
    INVALID_NAME = 12
    INVALID_EMAIL = 13
    DUPLICATE_NAME = 14
    ACCESS_DENIED = 15
    TIMEOUT = 16
    BANNED = 17
    ACCOUNT_NOT_FOUND = 18
    INVALID_STEAM_ID = 19
    SERVICE_UNAVAILABLE = 20
    NOT_LOGGED_ON = 21
    PENDING = 22
    ENCRYPTION_FAILURE = 23
    INSUFFICIENT_PRIVILEGE = 24
    LIMIT_EXCEEDED = 25
    REVOKED = 26
    EXPIRED = 27
    ALREADY_REDEEMED = 28
    DUPLICATE_REQUEST = 29
    ALREADY_OWNED = 30
    IP_NOT_FOUND = 31
    PERSIST_FAILED = 32
    LOCKING_FAILED = 33
    LOGON_SESSION_REPLACED = 34
    CONNECT_FAILED = 35
    HANDSHAKE_FAILED = 36
    IO_FAILURE = 37
    REMOTE_DISCONNECT = 38
    SHOPPING_CART_NOT_FOUND = 39
    BLOCKED = 40
    IGNORED = 41
    NO_MATCH = 42
    ACCOUNT_DISABLED = 43
    SERVICE_READ_ONLY = 44
    ACCOUNT_NOT_FEATURED = 45
    ADMINISTRATOR_OK = 46
    CONTENT_VERSION = 47
    TRY_ANOTHER_CM = 48
    PASSWORD_REQUIRED_TO_KICK_SESSION = 49
    ALREADY_LOGGED_IN_ELSEWHERE = 50
    SUSPENDED = 51
    CANCELLED = 52
    DATA_CORRUPTION = 53
    DISK_FULL = 54
    REMOTE_CALL_FAILED = 55
    PASSWORD_UNSET = 56
    EXTERNAL_ACCOUNT_UNLINKED = 57
    PSN_TICKET_INVALID = 58
    EXTERNAL_ACCOUNT_ALREADY_LINKED = 59
    REMOTE_FILE_CONFLICT = 60
    ILLEGAL_PASSWORD = 61
    SAME_AS_PREVIOUS_VALUE = 62
    ACCOUNT_LOGON_DENIED = 63
    CANNOT_USE_OLD_PASSWORD = 64
    INVALID_LOGIN_AUTH_CODE = 65
    ACCOUNT_LOGON_DENIED_NO_MAIL = 66
    HARDWARE_NOT_CAPABLE_OF_IPT = 67
    IPT_INIT_ERROR = 68
    PARENTAL_CONTROL_RESTRICTED = 69
    FACEBOOK_QUERY_ERROR = 70
    EXPIRED_LOGIN_AUTH_CODE = 71
    IP_LOGIN_RESTRICTION_FAILED = 72
    ACCOUNT_LOCKED_DOWN = 73
    ACCOUNT_LOGON_DENIED_VERIFIED_EMAIL_REQUIRED = 74
    NO_MATCHING_URL = 75
    BAD_RESPONSE = 76
    REQUIRE_PASSWORD_RE_ENTRY = 77
    VALUE_OUT_OF_RANGE = 78
    UNEXPECTED_ERROR = 79
    DISABLED = 80
    INVALID_CEG_SUBMISSION = 81
    RESTRICTED_DEVICE = 82
    REGION_LOCKED = 83
    RATE_LIMIT_EXCEEDED = 84
    ACCOUNT_LOGIN_DENIED_NEED_TWO_FACTOR = 85
    ITEM_DELETED = 86
    ACCOUNT_LOGIN_DENIED_THROTTLE = 87
    TWO_FACTOR_CODE_MISMATCH = 88
    TWO_FACTOR_ACTIVATION_CODE_MISMATCH = 89
    ACCOUNT_ASSOCIATED_TO_MULTIPLE_PARTNERS = 90
    NOT_MODIFIED = 91
    NO_MOBILE_DEVICE = 92
    TIME_NOT_SYNCED = 93
    SMS_CODE_FAILED = 94
    ACCOUNT_LIMIT_EXCEEDED = 95
    ACCOUNT_ACTIVITY_LIMIT_EXCEEDED = 96
    PHONE_ACTIVITY_LIMIT_EXCEEDED = 97
    REFUND_TO_WALLET = 98
    EMAIL_SEND_FAILURE = 99
    NOT_SETTLED = 100
    NEED_CAPTCHA = 101
    GSLT_DENIED = 102
    GS_OWNER_DENIED = 103
    INVALID_ITEM_TYPE = 104
    IP_BANNED = 105
    GSLT_EXPIRED = 106
    INSUFFICIENT_FUNDS = 107
    TOO_MANY_PENDING = 108
    NO_SITE_LICENSES_FOUND = 109
    WG_NETWORK_SEND_EXCEEDED = 110
    ACCOUNT_NOT_FRIENDS = 111
    LIMITED_USER_ACCOUNT = 112
    CANT_REMOVE_ITEM = 113
    ACCOUNT_HAS_BEEN_DELETED = 114
    ACCOUNT_HAS_AN_EXISTING_USER_CANCELLED_LICENSE = 115
    DENIED_DUE_TO_COMMUNITY_COOLDOWN = 116
    NO_LAUNCHER_SPECIFIED = 117
    MUST_AGREE_TO_SSA = 118
    CLIENT_NO_LONGER_SUPPORTED = 119
