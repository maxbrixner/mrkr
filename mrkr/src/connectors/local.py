# ---------------------------------------------------------------------------- #

import pathlib
import hashlib
from typing import List

# ---------------------------------------------------------------------------- #

from .base import BaseConnector, FileObject

# ---------------------------------------------------------------------------- #


class LocalConnector(BaseConnector):
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
                    etag=self.get_checksum(file)
                )
            )

        return result

    def get_checksum(self, filename: pathlib.Path) -> str:
        """
        Get the checksum of a file.
        """
        sha256 = hashlib.sha256()

        with open(filename, "rb") as f:
            while chunk := f.read(4096):
                sha256.update(chunk)

        return sha256.hexdigest()


# ---------------------------------------------------------------------------- #
