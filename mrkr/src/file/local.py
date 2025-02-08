# ---------------------------------------------------------------------------- #

import pathlib
import hashlib
import contextlib
import io
from typing import List, Generator

# ---------------------------------------------------------------------------- #

from .base import BaseFileProvider, FileObject

# ---------------------------------------------------------------------------- #


class LocalFileProvider(BaseFileProvider):
    """
    The LocalConnector class is used to retrieve local data.
    """

    def list_files(
        self,
        uri: str
    ) -> List[FileObject]:
        """
        List all files in a directory.
        """
        files = sorted(pathlib.Path("data").glob(uri))

        if len(files) == 0:
            return []

        result = []
        for file in files:
            result.append(
                FileObject(
                    name=file.name,
                    uri=str(file.resolve()),
                    etag=self.get_checksum(str(file))
                )
            )

        return result

    @contextlib.contextmanager
    def read_file(
        self,
        uri: str
    ) -> Generator[io.BufferedReader]:
        """
        Yields a binary file stream.
        """
        filename = pathlib.Path(uri)

        if not filename.is_file():
            raise FileNotFoundError(f"File {filename} not found.")

        with pathlib.Path(uri).open("rb") as file:
            yield file

# ---------------------------------------------------------------------------- #
