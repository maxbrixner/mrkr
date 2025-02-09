
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

class SourceProvider(str, enum.Enum):
    local = "local"
    s3 = "s3"


class ProjectStatus(str, enum.Enum):
    scan_pending = "scan_pending"
    scan_running = "scan_running"
    scan_failed = "scan_failed"
    ready = "ready"


class Project(sqlmodel.SQLModel, table=True):
    __tablename__ = "tproject"
    id: int = sqlmodel.Field(primary_key=True)
    name: str = sqlmodel.Field()
    description: str = sqlmodel.Field()
    creator_id: int = sqlmodel.Field(foreign_key="tuser.id")
    provider: SourceProvider = sqlmodel.Field()
    uri: str = sqlmodel.Field()
    status: ProjectStatus = sqlmodel.Field()
    last_scan: Optional[datetime.datetime] = sqlmodel.Field()

    creator: User = sqlmodel.Relationship()
    tasks: List["Task"] = sqlmodel.Relationship(back_populates="project")
    labeltypes: List["LabelType"] = sqlmodel.Relationship(
        back_populates="project")


class LabelCategory(str, enum.Enum):
    word = "word"


class LabelType(sqlmodel.SQLModel, table=True):
    __tablename__ = "tlabeltype"
    id: int = sqlmodel.Field(primary_key=True)
    project_id: int = sqlmodel.Field(foreign_key="tproject.id")
    name: str = sqlmodel.Field(unique=True)
    category: LabelCategory = sqlmodel.Field()
    color: str = sqlmodel.Field()

    project: Project = sqlmodel.Relationship()


class FileObject(sqlmodel.SQLModel, table=False):
    name: str = sqlmodel.Field()
    uri: str = sqlmodel.Field()
    etag: str = sqlmodel.Field()


class TaskStatus(str, enum.Enum):
    ocr_pending = "ocr_pending"
    ocr_running = "ocr_running"
    ocr_failed = "ocr_failed"
    ready = "ready"
    error = "error"


class Task(sqlmodel.SQLModel, table=True):
    __tablename__ = "ttask"
    id: int = sqlmodel.Field(primary_key=True)
    project_id: int = sqlmodel.Field(foreign_key="tproject.id")
    name: str = sqlmodel.Field()
    created: datetime.datetime = sqlmodel.Field()
    status: TaskStatus = sqlmodel.Field()
    abandoned: bool = sqlmodel.Field()
    uri: str = sqlmodel.Field()
    last_ocr: Optional[datetime.datetime] = sqlmodel.Field()

    project: Project = sqlmodel.Relationship()
    ocr: Optional["Ocr"] = sqlmodel.Relationship(back_populates="task")
    labels: List["Label"] = sqlmodel.Relationship(back_populates="task")


class OcrProvider(str, enum.Enum):
    tesseract = "tesseract"


class Ocr(sqlmodel.SQLModel, table=True):
    __tablename__ = "tocr"
    id: int = sqlmodel.Field(primary_key=True)
    task_id: int = sqlmodel.Field(foreign_key="ttask.id")
    etag: str = sqlmodel.Field()
    provider: OcrProvider = sqlmodel.Field()
    created: datetime.datetime = sqlmodel.Field()

    task: Task = sqlmodel.Relationship()
    pages: List["Page"] = sqlmodel.Relationship(back_populates="ocr")


class Page(sqlmodel.SQLModel, table=True):
    __tablename__ = "tpage"
    id: int = sqlmodel.Field(primary_key=True)
    ocr_id: int = sqlmodel.Field(foreign_key="tocr.id")
    page: int = sqlmodel.Field()
    width: float = sqlmodel.Field()
    height: float = sqlmodel.Field()

    ocr: Ocr = sqlmodel.Relationship()
    blocks: List["Block"] = sqlmodel.Relationship(back_populates="page")


class BlockType(str, enum.Enum):
    word = "word"


class BlockObject(sqlmodel.SQLModel, table=False):
    type: BlockType = sqlmodel.Field()
    content: str = sqlmodel.Field()
    confidence: Optional[float] = sqlmodel.Field()
    left: float = sqlmodel.Field()
    top: float = sqlmodel.Field()
    width: float = sqlmodel.Field()
    height: float = sqlmodel.Field()


class Block(BlockObject, table=True):
    __tablename__ = "tblock"
    id: int = sqlmodel.Field(primary_key=True)
    page_id: int = sqlmodel.Field(foreign_key="tpage.id")

    page: Page = sqlmodel.Relationship()
    link: Optional["LabelLink"] = sqlmodel.Relationship(
        back_populates="block")


class Label(sqlmodel.SQLModel, table=True):
    __tablename__ = "tlabel"
    id: int = sqlmodel.Field(primary_key=True)
    task_id: int = sqlmodel.Field(foreign_key="ttask.id")
    labeltype_id: int = sqlmodel.Field(
        foreign_key="tlabeltype.id")
    user_content: str = sqlmodel.Field()

    task: Task = sqlmodel.Relationship()
    links: List["LabelLink"] = sqlmodel.Relationship(
        back_populates="label")
    labeltype: LabelType = sqlmodel.Relationship()


class LabelLink(sqlmodel.SQLModel, table=True):
    __tablename__ = "tlabellink"
    id: int = sqlmodel.Field(primary_key=True)
    label_id: int = sqlmodel.Field(foreign_key="tlabel.id")
    block_id: int = sqlmodel.Field(foreign_key="tblock.id")

    label: Label = sqlmodel.Relationship()
    block: Block = sqlmodel.Relationship()

# ---------------------------------------------------------------------------- #
