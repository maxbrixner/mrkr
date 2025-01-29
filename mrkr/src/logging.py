# ---------------------------------------------------------------------------- #

import os
import json
import pathlib
import logging
import logging.config

# ---------------------------------------------------------------------------- #

from typing import Optional

# ---------------------------------------------------------------------------- #


class Logger():

    logger: logging.Logger

    def __init__(self, name: Optional[str] = None) -> None:
        """
        Initialize the Logger. The logging configuration is read from
        the file logging/{LOGGING_CONFIG}.json, where LOGGING_CONFIG is an
        environment variable.
        """
        self.logger = logging.getLogger(name)

        if self.logger.hasHandlers():
            return

        logging_config = pathlib.Path(__file__).parent.parent / \
            pathlib.Path(f"config/{os.getenv('LOGGING_CONFIG')}.json")

        if not logging_config.is_file():
            return

        with logging_config.open('r') as file:
            logging.config.dictConfig(json.loads(file.read()))

    def debug(self, message: str) -> None:
        """
        Log a message with severity DEBUG.
        """
        self.logger.debug(message)

    def info(self, message: str) -> None:
        """
        Log a message with severity INFO.
        """
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """
        Log a message with severity WARNING.
        """
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """
        Log a message with severity ERROR.
        """
        self.logger.error(message)

    def critical(self, message: str) -> None:
        """
        Log a message with severity CRITICAL.
        """
        self.logger.critical(message)

    def exception(self, exception: Exception) -> None:
        """
        Log a message with severity ERROR and include exception information.
        """
        self.logger.exception(exception)

# ---------------------------------------------------------------------------- #
