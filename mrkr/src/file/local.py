# ---------------------------------------------------------------------------- #

import pathlib
import hashlib
import contextlib
from typing import List

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
        files = sorted(pathlib.Path("test").glob(uri))

        if len(files) == 0:
            return []

        result = []
        for file in files:
            result.append(
                FileObject(
                    name=file.name,
                    uri=str(file),
                    etag=self._get_checksum(file)
                )
            )

        return result

    @contextlib.contextmanager
    def read_file(
        self,
        uri: str
    ):
        """
        Yields a binary file stream.
        """
        filename = pathlib.Path(uri)

        if not filename.is_file():
            raise FileNotFoundError(f"File {filename} not found.")

        with pathlib.Path(uri).open("rb") as file:
            yield file

# ---------------------------------------------------------------------------- #
