# ---------------------------------------------------------------------------- #

import sqlmodel
import sqlalchemy
import os
import logging
from typing import Any, Generator
from contextlib import contextmanager

# ---------------------------------------------------------------------------- #

from .config import *

# ---------------------------------------------------------------------------- #


class DatabaseSession(sqlmodel.Session):
    """
    A child of the SQLModel session that provides additional functionality.
    """
    logger: logging.Logger

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger('mrkr.database')
        self.logger.debug("New database session initialized.")

    def commit(self) -> None:
        """
        Commit the session.
        """
        self.logger.debug("Committing to database session.")

        try:
            super().commit()
        except Exception as exception:
            self.logger.exception(exception)
            raise Exception("Unable to commit to database session.")

# ---------------------------------------------------------------------------- #


class Database():
    """
    A wrapper for the SQLModel connection that utilizes environment variables
    to establish a connection.
    """
    alias: str
    host: str | None
    port: str | None
    user: str | None
    password: str | None
    database: str | None

    engine: sqlalchemy.engine.base.Engine | None
    logger: logging.Logger

    def __init__(
        self,
        alias: str
    ) -> None:
        """
        Initialize the AsyncDatabase class.
        """
        self.logger = logging.getLogger('mrkr.database')

        self.alias = alias
        self.host = os.getenv(f"{alias}_HOST")
        self.port = os.getenv(f"{alias}_PORT")
        self.user = os.getenv(f"{alias}_USER")
        self.password = os.getenv(f"{alias}_PASSWORD")
        self.database = os.getenv(f"{alias}_DATABASE")

        self.engine = None

        self.logger.debug(f"Database with alias = {alias} initialized.")

    def connect(
        self
    ) -> None:
        """
        Attempt to establish a connection.
        """
        if self.engine is not None:
            return

        connection_string = f"postgresql://{self.user}:" \
            f"{self.password}@{self.host}:{self.port}/{self.database}"

        try:
            self.engine = sqlmodel.create_engine(connection_string)
        except Exception as exception:
            self.logger.exception(exception)
            raise Exception("Unable to create database engine.")

        if self.engine is None:
            raise Exception(
                f"Unable to create database engine for alias = {self.alias}.")

        self.logger.debug(
            f"Database connection for alias = {self.alias} established.")

    def create_tables(self) -> None:
        self.connect()

        if self.engine is None:
            raise Exception(
                f"Unable to create database engine for alias = {self.alias}.")

        sqlmodel.SQLModel.metadata.create_all(self.engine)

    def drop_tables(self) -> None:
        self.connect()

        if self.engine is None:
            raise Exception(
                f"Unable to create database engine for alias = {self.alias}.")

        sqlmodel.SQLModel.metadata.drop_all(self.engine)

    def get_database_session(self) -> DatabaseSession:
        """
        Get a session from the database engine.
        """
        self.connect()

        return DatabaseSession(self.engine)

    @contextmanager
    def session(self) -> Generator[DatabaseSession]:
        """
        Get a session from the database engine.
        """
        self.connect()

        with DatabaseSession(self.engine) as session:
            yield session

# ---------------------------------------------------------------------------- #
