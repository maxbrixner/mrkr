# ---------------------------------------------------------------------------- #

import pydantic

# ---------------------------------------------------------------------------- #

from .models import FlashMessage, FlashType, UserFlashMessage


# ---------------------------------------------------------------------------- #


class HtmxConfig(pydantic.BaseModel):
    # artificial delay (in milliseconds) that is added to htmx requests
    # in order to avoid flickering
    swap_delay: int = 500
    # request timeout
    timeout: int = 20000


class Config(pydantic.BaseModel):
    htmx_config: HtmxConfig = HtmxConfig()
    # length of the random csrf token
    csrf_token_length: int = 32
    # name of the session id to be used in the http header/browser
    session_name: str = "session_id"
    # session timeout in seconds
    session_timeout: int = 300
    # length of the random session token
    session_token_length: int = 32
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
