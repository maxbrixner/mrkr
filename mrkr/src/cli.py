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

        project = Project(
            name="Demo Project",
            description="A simple demo project.",
            creator=user,
            source_type=SourceType.local,
            source_uri="*.*",
            scan_status=ScanStatus.initialized
        )

        session.add(project)
        session.commit()

        label1 = Label(
            project=project,
            name="Name",
            color="#648fff"
        )

        label2 = Label(
            project=project,
            name="Street",
            color="#dc267f"
        )

        label3 = Label(
            project=project,
            name="IBAN",
            color="#ffb000"
        )

        session.add(label1)
        session.add(label2)
        session.add(label3)

        session.commit()

    logger.info("Demo data inserted.")

# ---------------------------------------------------------------------------- #
