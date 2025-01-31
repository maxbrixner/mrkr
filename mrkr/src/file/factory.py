# ---------------------------------------------------------------------------- #

from typing import Optional

# ---------------------------------------------------------------------------- #

from .base import BaseFileProvider
from .local import LocalFileProvider

# ---------------------------------------------------------------------------- #


class FileProviderFactory():
    """
    Factory for file providers.
    """
    @staticmethod
    def get_provider(provider: Optional[str] = None) -> BaseFileProvider:
        """
        Get OCR provider by name.
        """
        match provider:
            case None:
                return LocalFileProvider()
            case "local":
                return LocalFileProvider()
            case _:
                raise Exception(f"Unknown file provider: {provider}")

# ---------------------------------------------------------------------------- #
