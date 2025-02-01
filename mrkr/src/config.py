# ---------------------------------------------------------------------------- #

import pydantic
import enum

# ---------------------------------------------------------------------------- #


class FlashMessage(str, enum.Enum):
    session_expired = "INFO_SESSION_EXPIRED"
    invalid_credentials = "ERROR_INVALID_CREDENTIALS"
    credentials_exist = "ERROR_CREDENTIALS_EXIST"
    signup_successful = "INFO_SIGNUP_SUCCESSFUL"
    signup_disabled = "ERROR_SIGNUP_DISABLED"
    too_many_login_attempts = "ERROR_TOO_MANY_LOGIN_ATTEMPTS"
    too_many_requests = "ERROR_TOO_MANY_REQUESTS"


class FlashType(str, enum.Enum):
    error = "ERROR"
    warning = "WARNING"
    info = "INFO"


class UserFlashMessage(pydantic.BaseModel):
    message: FlashMessage
    user_message: str
    type: FlashType

# ---------------------------------------------------------------------------- #


class Localization(pydantic.BaseModel):
    firstweekday: int = 6  # 0 for Monday, 6 for Sunday
    month_year_format: str = "%b %Y"
    month_format: str = "%b"
    day_format: str = "%d"
    day_month_format: str = "%b %d"
    day_month_year_format: str = "%b %d, %Y"
    day_of_week_format: str = "%a"
    weekdays: list[str] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# ---------------------------------------------------------------------------- #


class HtmxConfig(pydantic.BaseModel):
    # artificial delay (in milliseconds) that is added to htmx requests
    # in order to avoid flickering
    swap_delay: int = 1000
    # timeout
    timeout: int = 20000


class Config(pydantic.BaseModel):
    htmx_config: HtmxConfig = HtmxConfig()

    # length of the random csrf token
    csrf_token_length: int = 32
    # dictionary containing localization configurations for each supported
    # language
    localization: dict[str, Localization] = {"en": Localization()}
    # length of the nonce for inline scripts
    nonce_length: int = 16
    # name of the session id to be used in the http header/browser
    session_name: str = "session_id"
    # session timeout in seconds
    session_timeout: int = 600
    # length of the random session token
    session_token_length: int = 32
    # artificial delay (in milliseconds) that is added to htmx requests
    # in order to avoid flickering
    swap_delay: int = 200
    # timeout
    timeout: int = 20000
    # whether to enforce csrf tokens
    force_csrf_token: bool = True
    # flash messages
    flash_messages: dict[FlashMessage, UserFlashMessage] = {
        FlashMessage.session_expired: UserFlashMessage(
            message=FlashMessage.session_expired,
            user_message="Your session has expired due to inactivity.",
            type=FlashType.info
        ),
        FlashMessage.invalid_credentials: UserFlashMessage(
            message=FlashMessage.invalid_credentials,
            user_message="You entered invalid credentials. Please try again.",
            type=FlashType.error
        ),
        FlashMessage.credentials_exist: UserFlashMessage(
            message=FlashMessage.credentials_exist,
            user_message="Sorry, these credentials already exist.",
            type=FlashType.error
        ),
        FlashMessage.signup_successful: UserFlashMessage(
            message=FlashMessage.signup_successful,
            user_message="Signup successful. Please proceed to login.",
            type=FlashType.info
        ),
        FlashMessage.signup_disabled: UserFlashMessage(
            message=FlashMessage.signup_disabled,
            user_message="Signup was disabled by your administrator.",
            type=FlashType.error
        ),
        FlashMessage.too_many_login_attempts: UserFlashMessage(
            message=FlashMessage.signup_disabled,
            user_message="Your account is currently disabled",
            type=FlashType.error
        ),
        FlashMessage.too_many_requests: UserFlashMessage(
            message=FlashMessage.signup_disabled,
            user_message="Your account is currently disabled",
            type=FlashType.error
        )
    }

# ---------------------------------------------------------------------------- #


config = Config()
