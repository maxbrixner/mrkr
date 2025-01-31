from typing import Optional

from .base import BaseOcrProvider
from .tesseract import TesseractOcrProvider


class OcrProviderFactory():
    """
    Factory for OCR providers.
    """
    @staticmethod
    def get_provider(provider: str) -> BaseOcrProvider:
        """
        Get OCR provider by name.
        """
        match provider:
            case "tesseract":
                return TesseractOcrProvider()
            case _:
                raise Exception(f"Unknown OCR provider: {provider}")
