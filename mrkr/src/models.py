
# ---------------------------------------------------------------------------- #

import sqlmodel
import datetime
import enum
import pydantic
from typing import Optional, List

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


# ---------------------------------------------------------------------------- #


class SourceType(str, enum.Enum):
    local = "local"
    s3 = "s3"


class ScanStatus(str, enum.Enum):
    initialized = "initialized"
    pending = "pending"
    scanning = "scanning"
    ready = "ready"
    error = "error"


class Project(sqlmodel.SQLModel, table=True):
    __tablename__ = "tproject"
    id: int = sqlmodel.Field(primary_key=True)
    name: str = sqlmodel.Field()
    description: str = sqlmodel.Field()
    creator_id: int = sqlmodel.Field(foreign_key="tuser.id")

    source_type: SourceType = sqlmodel.Field()
    source_uri: str = sqlmodel.Field()

    scan_status: ScanStatus = sqlmodel.Field()
    last_scan: datetime.datetime = sqlmodel.Field(nullable=True)

    creator: User = sqlmodel.Relationship()


class LabelDefinition(sqlmodel.SQLModel, table=True):
    __tablename__ = "tlabeldefinition"
    id: int = sqlmodel.Field(primary_key=True)
    project_id: int = sqlmodel.Field(foreign_key="tproject.id")
    name: str = sqlmodel.Field(unique=True)
    color: str = sqlmodel.Field()

    project: Project = sqlmodel.Relationship()


# ---------------------------------------------------------------------------- #

class OcrBlockType(str, enum.Enum):
    word = "word"


class OcrResult(sqlmodel.SQLModel, table=True):
    __tablename__ = "tocrresult"
    id: int = sqlmodel.Field(primary_key=True)
    etag: str = sqlmodel.Field()
    provider: str = sqlmodel.Field()
    created: datetime.datetime = sqlmodel.Field()


class OcrPage(sqlmodel.SQLModel, table=True):
    __tablename__ = "tocrpage"
    id: int = sqlmodel.Field(primary_key=True)
    ocr_id: int = sqlmodel.Field(foreign_key="tocrresult.id")
    page: int = sqlmodel.Field()
    width: float = sqlmodel.Field()
    height: float = sqlmodel.Field()


class OcrBlock(sqlmodel.SQLModel, table=True):
    __tablename__ = "tocrblock"
    id: int = sqlmodel.Field(primary_key=True)
    page_id: int = sqlmodel.Field(foreign_key="tocrpage.id")
    type: OcrBlockType = sqlmodel.Field()
    content: str = sqlmodel.Field()
    confidence: Optional[float] = sqlmodel.Field()
    left: float = sqlmodel.Field()
    top: float = sqlmodel.Field()
    width: float = sqlmodel.Field()
    height: float = sqlmodel.Field()


# ---------------------------------------------------------------------------- #


class TaskStatus(str, enum.Enum):
    open = "open"
    progress = "progress"
    complete = "complete"


class FileStatus(str, enum.Enum):
    found = "found"
    missing = "missing"


class OcrStatus(str, enum.Enum):
    initialized = "initialized"
    pending = "pending"
    scanning = "scanning"
    ready = "ready"
    error = "error"


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
    uri: str = sqlmodel.Field(unique=True)

    task_status: TaskStatus = sqlmodel.Field()
    file_status: FileStatus = sqlmodel.Field()
    ocr_status: OcrStatus = sqlmodel.Field()

    project: Project = sqlmodel.Relationship()
    ocr: OcrResult = sqlmodel.Relationship()


class LabelObject(pydantic.BaseModel):
    label_id: int
    ocr_ids: List[int]
    user_content: str


class UserLabel(sqlmodel.SQLModel, table=True):
    __tablename__ = "tuserlabel"
    id: int = sqlmodel.Field(primary_key=True)
    task_id: int = sqlmodel.Field(foreign_key="ttask.id")
    label_id: int = sqlmodel.Field(foreign_key="tlabel.id")
    user_content: str = sqlmodel.Field()

# ---------------------------------------------------------------------------- #
