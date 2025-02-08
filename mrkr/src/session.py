# ---------------------------------------------------------------------------- #

from fastapi import Request, HTTPException
import secrets
import sqlmodel
import bcrypt
import logging
import datetime
from typing import Callable, Self, Optional

# ---------------------------------------------------------------------------- #

from .config import *
from .database import *
from .models import *

# ---------------------------------------------------------------------------- #


class SessionManager():

    logger: logging.Logger

    request: Request
    session: Session | None

    _database: Database
    _database_session: DatabaseSession
    _force_authentication: bool

    def __init__(
        self,
        database: Database,
        request: Request,
        force_authentication: bool = False
    ) -> None:
        """
        Initialize the HTTP session.
        """
        self.logger = logging.getLogger('mrkr.session')

        self.request = request
        self.session = None

        self._database = database
        self._database_session = self._database.get_database_session()

        self._force_authentication = force_authentication

    async def establish_session(self) -> None:
        """
        Establish a session by resuming a (non-expired) session or creating a
        new session.
        """
        await self._resume_session()

        if not self.session:
            self.logger.debug("No session resumed.")
            await self._create_session()

        if await self.is_expired():
            self.logger.debug("Session has expired.")
            await self._create_session()
            await self.add_flash_message(FlashMessage.session_expired)

        if not self.session:
            raise Exception("Session could not be established.")

        if not self.session or \
                (not self.session.user and self._force_authentication):
            self.logger.warning(f"Unauthorized access attempt.")
            raise HTTPException(status_code=401, detail="Unauthorized")

        if config.force_csrf_token:
            await self._check_csrf_token()

        self.logger.debug("Session established.")

    async def _resume_session(self) -> None:
        """
        Resume a session by checking the session token in the request. Does
        not check if the session has expired.
        """
        session_token = self.request.cookies.get(config.session_name)

        if not session_token:
            self.logger.debug("No session token passed.")
            self.session = None
            return

        query = sqlmodel.select(Session).where(
            Session.session_token == session_token
        )

        session = self._database_session.exec(query).first()

        if not session:
            self.logger.warning("Invalid session token.")
            self.session = None
            return

        self.session = session

        await self._refresh_session()

        self.request.state.session_token = self.session.session_token
        self.request.state.csrf_token = self.session.csrf_token

        self.logger.debug("Session resumed.")

    async def _create_session(self, user: User | None = None) -> None:
        """
        Create a new session.
        """
        if user:
            csrf_token = await self._generate_token(config.csrf_token_length)
        else:
            csrf_token = None

        session = Session(
            updated=datetime.datetime.now(datetime.timezone.utc),
            user=user,
            session_token=await self._generate_token(
                config.session_token_length),
            csrf_token=csrf_token
        )

        self._database_session.add(session)
        self._database_session.commit()

        self.session = session

        self.request.state.session_token = self.session.session_token
        self.request.state.csrf_token = self.session.csrf_token

        self.logger.debug("New session created.")

    async def _refresh_session(self) -> None:
        """
        Update the session's timestamp.
        """
        if self.session is None:
            raise Exception("Cannot refresh a non-existent session.")

        self.session.updated = datetime.datetime.now(
            datetime.timezone.utc
        )
        self._database_session.add(self.session)
        self._database_session.commit()

        self.logger.debug("Session refreshed.")

    async def login(self, email: str, password: str) -> None:
        """
        Attempt a login by checking the provided username and password against
        the password hash in the database. If the login is successful,
        a new session is created.
        """
        query = sqlmodel.select(Authentication).where(
            Authentication.email == email
        )
        authentication = self._database_session.exec(query).first()

        if not isinstance(authentication, Authentication):
            self.logger.warning(f"Login attempt with unknown email.")
            await self.add_flash_message(FlashMessage.invalid_credentials)
            raise HTTPException(status_code=401, detail="Unauthorized")

        if not await self._check_password(
            plain_password=password,
            password_hash=authentication.password_hash
        ):
            self.logger.warning(f"Login attempt with invalid password "
                                f"for user '{authentication.user_id}'.")
            await self.add_flash_message(FlashMessage.invalid_credentials)
            raise HTTPException(status_code=401, detail="Unauthorized")

        await self._create_session(user=authentication.user)

        self.logger.debug(
            f"Login for user {authentication.user_id} successful.")

    async def logout(self) -> None:
        """
        Logout the user by deleting the session.
        """
        session = self.session
        if session:
            self._database_session.delete(session)
            self._database_session.commit()
        self.session = None

        self.logger.debug("Logout successful.")

    async def signup(
        self,
        username: str,
        email: str,
        password: str
    ) -> None:
        """
        Create a new user and credentials in the database.
        """
        query_authentication = sqlmodel.select(Authentication).where(
            Authentication.email == email
        )
        if self._database_session.exec(query_authentication).first():
            self.logger.error(f"Signup credentials already exist.")
            await self.add_flash_message(FlashMessage.credentials_exist)
            raise HTTPException(status_code=409, detail="Conflict")

        query_user = sqlmodel.select(User).where(
            User.name == username
        )
        if self._database_session.exec(query_user).first():
            self.logger.error(f"Signup credentials already exist.")
            await self.add_flash_message(FlashMessage.credentials_exist)
            raise HTTPException(status_code=409, detail="Conflict")

        user = User(name=username)

        authentication = Authentication(
            email=email,
            password_hash=await self._hash_password(plain_password=password),
            user=user
        )

        self._database_session.add(user)
        self._database_session.add(authentication)
        self._database_session.commit()

        await self.add_flash_message(FlashMessage.signup_successful)

        self.logger.error(f"Signup successful.")

    @property
    def database(self) -> DatabaseSession:
        """
        Return the underlying database session.
        """
        return self._database_session

    @property
    def user(self) -> User | None:
        """
        Return the session's user.
        """
        if self.session is None:
            return None
        return self.session.user

    @property
    def session_token(self) -> str | None:
        """
        Return the session's token (as known to the web browser).
        """
        if self.session is None:
            return None
        return self.session.session_token

    @property
    def updated(self) -> datetime.datetime | None:
        """
        Return the session's updated timestamp.
        """
        if self.session is None:
            return None
        return self.session.updated

    @property
    def csrf_token(self) -> str | None:
        """
        Return the session's csrf token.
        """
        if self.session is None:
            return None
        return self.session.csrf_token

    @property
    def flash(self) -> FlashMessage | None:
        """
        Return the session's flash message.
        """
        if self.session is None:
            return None
        return self.session.flash

    async def add_flash_message(self, message: FlashMessage) -> None:
        """
        Set the session's flash message.
        """
        if self.session is None:
            return
        self.session.flash = message
        self._database_session.add(self.session)
        self._database_session.commit()

        self.logger.debug(f"Flash message set: {message}")

    async def pop_flash_message(self) -> UserFlashMessage | None:
        """
        Return the session's flash message as a user text and delete it.
        """
        if self.session is None:
            return None
        flash = self.session.flash

        if flash is None:
            return None

        self.session.flash = None
        self._database_session.add(self.session)
        self._database_session.commit()

        if flash in config.flash_messages:
            return config.flash_messages[flash]

        return None

    async def is_authenticated(self) -> bool:
        """
        Check if the session is authenticated.
        """
        if self.session is None:
            return False

        if self.session.user is None:
            return False
        return True

    async def is_expired(self) -> bool:
        """
        Check if the session has expired.
        """
        if self.session is None:
            return False

        if config.session_timeout == 0:
            return False

        if self.updated is None:
            return True

        session_updated = self.updated.replace(tzinfo=datetime.timezone.utc)

        delta = datetime.datetime.now(datetime.timezone.utc) - session_updated

        if delta.total_seconds() > config.session_timeout:
            return True

        return False

    @staticmethod
    def get_session(database: Database) -> Callable:
        """
        A getter for the FastAPI dependency injection.
        """
        async def getter(request: Request) -> SessionManager:
            manager = SessionManager(
                database, request)
            await manager.establish_session()
            return manager
        return getter

    @staticmethod
    def get_authenticated_session(database: Database) -> Callable:
        """
        A getter for the FastAPI dependency injection. Requires authentication.
        """
        async def getter(request: Request) -> SessionManager:
            manager = SessionManager(
                database, request, force_authentication=True)
            await manager.establish_session()
            return manager
        return getter

    async def _check_password(
        self,
        plain_password: str,
        password_hash: str
    ) -> bool:
        """
        Use bcrypt to check a password.
        """
        result = bcrypt.checkpw(
            plain_password.encode(),
            password_hash.encode()
        )

        return result

    async def _hash_password(
        self,
        plain_password: str,
    ) -> str:
        """
        Use bcrypt to hash a plain password.
        """
        salt = bcrypt.gensalt()

        result = bcrypt.hashpw(plain_password.encode(), salt)

        return result.decode()

    async def _generate_token(
        self,
        length: int = 32
    ) -> str:
        """
        Create a nonce for the content security policy.
        """
        return secrets.token_hex(nbytes=length)

    async def _check_csrf_token(self) -> None:
        """
        Check if the provided CSRF token is valid.
        """
        if self.session is None:
            return

        if self.session.csrf_token is None:
            return

        form_data = await self.request.form()

        if len(form_data) == 0:
            return

        if form_data.get("csrf_token") != self.session.csrf_token:
            self.logger.warning("Invalid CSRF token.")
            raise HTTPException(status_code=403, detail="Forbidden")

        self.logger.debug("CSRF token valid.")

    def __del__(self) -> None:
        """
        Close the database session.
        """
        self._database_session.close()
        self.logger.debug("Database session closed.")

# ---------------------------------------------------------------------------- #
