# ---------------------------------------------------------------------------- #

import sqlmodel
import sqlalchemy
import os
import enum
import logging
import datetime
from typing import Any, Generator, Optional, List
from contextlib import contextmanager

# ---------------------------------------------------------------------------- #

from .config import *
from .ocr import OcrObject

# ---------------------------------------------------------------------------- #


class User(sqlmodel.SQLModel, table=True):
    __tablename__ = "tuser"
    id: int = sqlmodel.Field(primary_key=True)
    name: str = sqlmodel.Field(unique=True)


class Authentication(sqlmodel.SQLModel, table=True):
    __tablename__ = "tauthentication"
    id: int = sqlmodel.Field(primary_key=True)
    email: str = sqlmodel.Field(unique=True)
    password_hash: str = sqlmodel.Field()
    user_id: int = sqlmodel.Field(foreign_key="tuser.id")

    user: User = sqlmodel.Relationship()


class Session(sqlmodel.SQLModel, table=True):
    __tablename__ = "tsession"
    id: int = sqlmodel.Field(primary_key=True)
    updated: datetime.datetime = sqlmodel.Field()
    user_id: Optional[int] = sqlmodel.Field(
        foreign_key="tuser.id", nullable=True)
    session_token: str = sqlmodel.Field(unique=True)
    csrf_token: Optional[str] = sqlmodel.Field(nullable=True)
    flash: Optional[FlashMessage] = sqlmodel.Field(nullable=True)

    user: User = sqlmodel.Relationship()


class SourceType(str, enum.Enum):
    local = "local"
    s3 = "s3"


class ProjectStatus(str, enum.Enum):
    error = "error"
    pending = "pending"
    unscanned = "unscanned"
    scanning = "scanning"
    scanned = "scanned"


class Project(sqlmodel.SQLModel, table=True):
    __tablename__ = "tproject"
    id: int = sqlmodel.Field(primary_key=True)
    name: str = sqlmodel.Field()
    description: str = sqlmodel.Field()
    creator_id: int = sqlmodel.Field(foreign_key="tuser.id")

    source_type: SourceType = sqlmodel.Field()
    source_uri: str = sqlmodel.Field()
    status: ProjectStatus = sqlmodel.Field()
    last_scan: datetime.datetime = sqlmodel.Field(nullable=True)

    creator: User = sqlmodel.Relationship()


class OcrStatus(str, enum.Enum):
    error = "error"
    unscanned = "unscanned"
    scanning = "scanning"
    scanned = "scanned"


class OcrResult(sqlmodel.SQLModel, table=True):
    __tablename__ = "tocrresult"
    id: int = sqlmodel.Field(primary_key=True)
    ocr: Optional[OcrObject] = sqlmodel.Field(
        default_factory=OcrObject, sa_type=sqlmodel.JSON)
    provider: str = sqlmodel.Field()
    created: datetime.datetime = sqlmodel.Field()


class TaskStatus(str, enum.Enum):
    open = "open"
    progress = "progress"
    complete = "complete"


class Task(sqlmodel.SQLModel, table=True):
    __tablename__ = "ttask"
    id: int = sqlmodel.Field(primary_key=True)
    project_id: int = sqlmodel.Field(
        foreign_key="tproject.id")
    ocr_id: Optional[int] = sqlmodel.Field(
        foreign_key="tocrresult.id", nullable=True)
    name: str = sqlmodel.Field()
    created: datetime.datetime = sqlmodel.Field()
    modified: datetime.datetime = sqlmodel.Field(nullable=True)
    status: TaskStatus = sqlmodel.Field()

    etag: str = sqlmodel.Field()
    uri: str = sqlmodel.Field(unique=True)

    project: Project = sqlmodel.Relationship()
    ocr: OcrResult = sqlmodel.Relationship()


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
