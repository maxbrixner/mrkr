
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


class Project(sqlmodel.SQLModel, table=True):
    __tablename__ = "tproject"
    id: int = sqlmodel.Field(primary_key=True)
    name: str = sqlmodel.Field()
    description: str = sqlmodel.Field()
    creator_id: int = sqlmodel.Field(foreign_key="tuser.id")

    creator: User = sqlmodel.Relationship()
    sources: List["Source"] = sqlmodel.Relationship(back_populates="project")
    labels: List["LabelDefinition"] = sqlmodel.Relationship(
        back_populates="project")


class LabelType(str, enum.Enum):
    word = "word"


class LabelDefinition(sqlmodel.SQLModel, table=True):
    __tablename__ = "tlabeldefinition"
    id: int = sqlmodel.Field(primary_key=True)
    project_id: int = sqlmodel.Field(foreign_key="tproject.id")
    name: str = sqlmodel.Field(unique=True)
    type: LabelType = sqlmodel.Field()
    color: str = sqlmodel.Field()

    project: Project = sqlmodel.Relationship()


class SourceProvider(str, enum.Enum):
    local = "local"
    s3 = "s3"


class SourceStatus(str, enum.Enum):
    initialized = "initialized"
    pending = "pending"
    scanning = "scanning"
    ready = "ready"
    error = "error"


class Source(sqlmodel.SQLModel, table=True):
    __tablename__ = "tsource"
    id: int = sqlmodel.Field(primary_key=True)
    project_id: int = sqlmodel.Field(foreign_key="tproject.id")
    uri: str = sqlmodel.Field()
    type: SourceProvider = sqlmodel.Field()  # rename provider?
    status: SourceStatus = sqlmodel.Field()
    last_scan: Optional[datetime.datetime] = sqlmodel.Field(nullable=True)

    project: Project = sqlmodel.Relationship()
    tasks: List["Task"] = sqlmodel.Relationship(back_populates="source")


class TaskStatus(str, enum.Enum):
    open = "open"
    progress = "progress"
    complete = "complete"


class Task(sqlmodel.SQLModel, table=True):
    __tablename__ = "ttask"
    id: int = sqlmodel.Field(primary_key=True)
    source_id: int = sqlmodel.Field(foreign_key="tsource.id")
    name: str = sqlmodel.Field()
    created: datetime.datetime = sqlmodel.Field()
    modified: datetime.datetime = sqlmodel.Field(nullable=True)
    status: TaskStatus = sqlmodel.Field()
    pattern: str = sqlmodel.Field()

    source: Source = sqlmodel.Relationship()
    files: List["File"] = sqlmodel.Relationship(back_populates="task")


class FileStatus(str, enum.Enum):
    found = "found"
    missing = "missing"


class FileObject(sqlmodel.SQLModel, table=False):
    name: str = sqlmodel.Field()
    uri: str = sqlmodel.Field()
    etag: str = sqlmodel.Field()


class File(FileObject, table=True):
    __tablename__ = "tfile"
    id: int = sqlmodel.Field(primary_key=True)
    task_id: int = sqlmodel.Field(foreign_key="ttask.id")
    status: FileStatus = sqlmodel.Field()

    task: Task = sqlmodel.Relationship()
    labels: List["Label"] = sqlmodel.Relationship(back_populates="file")


# ---------------------------------------------------------------------------- #

class OcrProvider(str, enum.Enum):
    tesseract = "tesseract"


class OcrResult(sqlmodel.SQLModel, table=True):
    __tablename__ = "tocrresult"
    id: int = sqlmodel.Field(primary_key=True)
    etag: str = sqlmodel.Field()
    provider: OcrProvider = sqlmodel.Field()
    created: datetime.datetime = sqlmodel.Field()

    pages: List["OcrPage"] = sqlmodel.Relationship(back_populates="ocr_result")


class OcrPage(sqlmodel.SQLModel, table=True):
    __tablename__ = "tocrpage"
    id: int = sqlmodel.Field(primary_key=True)
    ocr_id: int = sqlmodel.Field(foreign_key="tocrresult.id")
    page: int = sqlmodel.Field()
    width: float = sqlmodel.Field()
    height: float = sqlmodel.Field()

    ocr_result: OcrResult = sqlmodel.Relationship()
    blocks: List["OcrBlock"] = sqlmodel.Relationship(back_populates="page")


class OcrBlockType(str, enum.Enum):
    word = "word"


class OcrBlockObject(sqlmodel.SQLModel, table=False):
    type: OcrBlockType = sqlmodel.Field()
    content: str = sqlmodel.Field()
    confidence: Optional[float] = sqlmodel.Field()
    left: float = sqlmodel.Field()
    top: float = sqlmodel.Field()
    width: float = sqlmodel.Field()
    height: float = sqlmodel.Field()


class OcrBlock(OcrBlockObject, table=True):
    __tablename__ = "tocrblock"
    id: int = sqlmodel.Field(primary_key=True)
    page_id: int = sqlmodel.Field(foreign_key="tocrpage.id")

    page: OcrPage = sqlmodel.Relationship()


# ---------------------------------------------------------------------------- #


class Label(sqlmodel.SQLModel, table=True):
    __tablename__ = "tlabel"
    id: int = sqlmodel.Field(primary_key=True)
    file_id: int = sqlmodel.Field(foreign_key="tfile.id")
    label_definition_id: int = sqlmodel.Field(
        foreign_key="tlabeldefinition.id")
    user_content: str = sqlmodel.Field()

    file: File = sqlmodel.Relationship()
    associations: List["LabelAssociation"] = sqlmodel.Relationship(
        back_populates="label")
    label_definition: LabelDefinition = sqlmodel.Relationship()


class LabelAssociation(sqlmodel.SQLModel, table=True):
    __tablename__ = "tlabelassociation"
    id: int = sqlmodel.Field(primary_key=True)
    label_id: int = sqlmodel.Field(foreign_key="tlabel.id")
    block_id: int = sqlmodel.Field(foreign_key="tocrblock.id")

    label: Label = sqlmodel.Relationship()
    block: OcrBlock = sqlmodel.Relationship()

# ---------------------------------------------------------------------------- #
