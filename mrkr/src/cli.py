# ---------------------------------------------------------------------------- #

import typer
import bcrypt
import dotenv
from typing import Optional

# ---------------------------------------------------------------------------- #

from .database import Database
from .logging import Logger
from .config import config
from .models import *

# ---------------------------------------------------------------------------- #

cli = typer.Typer()
logger = Logger("mrkr.cli")

dotenv.load_dotenv(".env")  # todo

# ---------------------------------------------------------------------------- #


@cli.command()
def create_tables() -> None:
    """
    Create all tables in the database.
    """
    Database(alias="POSTGRES").create_tables()

    logger.info("Tables created.")

# ---------------------------------------------------------------------------- #


@cli.command()
def drop_tables() -> None:
    """
    Drop all tables from the database.
    """
    Database(alias="POSTGRES").drop_tables()

    logger.info("Tables dropped.")

# ---------------------------------------------------------------------------- #


@cli.command()
def insert_demo() -> None:
    """
    Insert some demo data into the database.
    """
    with Database(alias="POSTGRES").session() as session:

        user = User(
            name="spongebob",
        )

        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw("test".encode(), salt).decode()

        authentication = Authentication(
            email="spongebob@bb.com",
            password_hash=password_hash,
            user=user
        )

        session.add(user)
        session.add(authentication)

        project = Project(
            name="Demo Project",
            description="A simple demo project.",
            creator=user
        )

        session.add(project)

        source1 = Source(
            project=project,
            uri="*",
            type=SourceProvider.local,
            status=SourceStatus.initialized
        )

        source2 = Source(
            project=project,
            uri="*.jpg",
            type=SourceProvider.local,
            status=SourceStatus.initialized
        )

        session.add(source1)
        session.add(source2)

        labeldef1 = LabelDefinition(
            project=project,
            name="Name",
            type=LabelType.word,
            color="#648fff"
        )

        labeldef2 = LabelDefinition(
            project=project,
            name="Street",
            type=LabelType.word,
            color="#dc267f"
        )

        labeldef3 = LabelDefinition(
            project=project,
            name="IBAN",
            type=LabelType.word,
            color="#ffb000"
        )

        session.add(labeldef1)
        session.add(labeldef2)
        session.add(labeldef3)

        session.commit()

    logger.info("Demo data inserted.")

# ---------------------------------------------------------------------------- #
