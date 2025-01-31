# ---------------------------------------------------------------------------- #

import logging
import pydantic
from typing import List

# ---------------------------------------------------------------------------- #


class FileObject(pydantic.BaseModel):
    """
    A file object.
    """
    name: str
    uri: str
    etag: str


# ---------------------------------------------------------------------------- #


class BaseConnector():
    """
    Base class for all connectors. A connector is a class that connects to a
    specific file service like AWS S3.
    """

    def __init__(self) -> None:
        """
        Initializes the connector.
        """
        self.logger = logging.getLogger(f"mrkr.connector")

    def list_files(
        self,
        uri: str
    ) -> List[FileObject]:
        """
        List all files in a directory.
        """
        raise NotImplementedError

# ---------------------------------------------------------------------------- #
