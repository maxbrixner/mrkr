# ---------------------------------------------------------------------------- #

import logging
import pydantic
import contextlib
import pathlib
import pdf2image
import hashlib
import io
from typing import List, Generator
from PIL import Image

# ---------------------------------------------------------------------------- #

from ..models import FileObject

# ---------------------------------------------------------------------------- #


class BaseFileProvider():
    """
    Base class for all file providers. A file provider is a class that connects
    to a specific file service like AWS S3.
    """

    def __init__(self) -> None:
        """
        Initializes the provider.
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

    @contextlib.contextmanager
    def read_file(
        self,
        uri: str
    ) -> Generator[io.BufferedReader, None, None]:
        """
        Yields a file stream.
        """
        raise NotImplementedError

    def file_to_image(
        self,
        uri: str
    ) -> List[Image.Image]:
        """
        Convert a file to a set of images.
        """
        filename = pathlib.Path(uri)

        try:
            if filename.suffix.lower() == ".pdf":
                return self._read_pdf_file(uri=uri)
            else:
                return self._read_image_file(uri=uri)
        except Exception as exception:
            self.logger.exception(exception)
            raise Exception(f"File '{uri}' could not be read.")

    def file_to_jpeg_bytes(
        self,
        uri: str,
        page: int = 0,
        quality: int = 95
    ) -> bytes:
        images = self.file_to_image(uri=uri)

        image_bytes = io.BytesIO()

        images[page].save(image_bytes, format="JPEG", quality=quality)

        image_bytes.seek(0)

        content = image_bytes.getvalue()

        return content

    def get_checksum(self, uri: str) -> str:
        """
        Get the checksum of a file.
        """
        sha256 = hashlib.sha256()

        with self.read_file(uri=uri) as file:
            while chunk := file.read(4096):
                sha256.update(chunk)

        return sha256.hexdigest()

    def _read_image_file(
        self,
        uri: str
    ) -> List[Image.Image]:
        with self.read_file(uri=uri) as file:
            image = Image.open(io.BytesIO(file.read()))
            return [image]

    def _read_pdf_file(
        self,
        uri: str
    ) -> List[Image.Image]:
        with self.read_file(uri=uri) as file:
            images = pdf2image.convert_from_bytes(file.read())
            return images

# ---------------------------------------------------------------------------- #
