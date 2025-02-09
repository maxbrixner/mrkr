# ---------------------------------------------------------------------------- #

import logging
from typing import List
from PIL import Image

# ---------------------------------------------------------------------------- #

from ..models import BlockObject

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

    def run_ocr(
        self,
        image: Image.Image
    ) -> List[BlockObject]:
        """
        Process an image and return the OCR results.
        """
        raise NotImplementedError

# ---------------------------------------------------------------------------- #
