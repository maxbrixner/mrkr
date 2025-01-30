# ---------------------------------------------------------------------------- #

import typer
import bcrypt
import logging
import pathlib
import dotenv
from typing import Optional

# ---------------------------------------------------------------------------- #

from .database import *
from .logging import Logger
from .config import config

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
        session.commit()

        project = Project(
            name="Demo Project",
            description="A simple demo project.",
            creator=user
        )

        session.add(project)
        session.commit()

        task = Task(
            project=project,
            name="Demo Document",
            creator=user,
            created=datetime.datetime.now(),
            status=TaskStatus.open,
            source=DocumentSource.local
        )

        session.add(task)
        session.commit()

        document = Document(
            task=task,
            filename="test/document1EN.pdf"
        )

        session.add(document)
        session.commit()

    logger.info("Demo data inserted.")

# ---------------------------------------------------------------------------- #
