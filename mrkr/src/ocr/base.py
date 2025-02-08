# ---------------------------------------------------------------------------- #

import logging
import pydantic
from typing import List, Optional, Tuple
from PIL import Image

# ---------------------------------------------------------------------------- #

from ..models import OcrResult

# ---------------------------------------------------------------------------- #


class BaseOcrProvider():
    """
    Base class for all OCR providers. An OCR provider is a class that runs
    optical character recognition on an image.
    """

    def __init__(self) -> None:
        """
        Initializes the provider.
        """
        self.logger = logging.getLogger("mrkr.ocr")

    def get_images(self) -> None:
        """
        Get the document as images.
        """
        raise NotImplementedError

    def run_ocr(
        self,
        images: List[Image.Image]
    ) -> OcrResult:
        """
        Process an image and return the OCR results.
        """
        raise NotImplementedError

# ---------------------------------------------------------------------------- #
