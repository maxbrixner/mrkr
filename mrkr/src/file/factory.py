# ---------------------------------------------------------------------------- #

from .base import BaseFileProvider
from .local import LocalFileProvider
from ..models import SourceProvider

# ---------------------------------------------------------------------------- #


class FileProviderFactory():
    """
    Factory for file providers.
    """
    @staticmethod
    def get_provider(provider: str) -> BaseFileProvider:
        """
        Get OCR provider by name.
        """
        match provider:
            case SourceProvider.local:
                return LocalFileProvider()
            case _:
                raise Exception(f"Unknown file provider: {provider}")

# ---------------------------------------------------------------------------- #
