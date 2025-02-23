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
        password_hash = bcrypt.hashpw("krabby".encode(), salt).decode()

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
            creator=user,
            provider=SourceProvider.local,
            uri="demo/*",
            status=ProjectStatus.ready,
        )

        session.add(project)

        labeltype1 = LabelType(
            project=project,
            name="Name",
            category=LabelCategory.word,
            color="#648fff"
        )

        labeltype2 = LabelType(
            project=project,
            name="Street",
            category=LabelCategory.word,
            color="#dc267f"
        )

        labeltype3 = LabelType(
            project=project,
            name="IBAN",
            category=LabelCategory.word,
            color="#ffb000"
        )

        session.add(labeltype1)
        session.add(labeltype2)
        session.add(labeltype3)

        session.commit()

    logger.info("Demo data inserted.")

# ---------------------------------------------------------------------------- #
