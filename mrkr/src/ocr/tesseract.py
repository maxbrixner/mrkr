# ---------------------------------------------------------------------------- #

import pydantic
import pytesseract
from PIL import Image
from typing import List, Tuple

# ---------------------------------------------------------------------------- #

from .base import BaseOcrProvider, OcrObject, OcrPage, OcrBlock, OcrCoordinates

# ---------------------------------------------------------------------------- #


class TesseractResult(pydantic.BaseModel):
    level: List[int]
    page_num: List[int]
    block_num: List[int]
    par_num: List[int]
    line_num: List[int]
    word_num: List[int]
    left: List[int]
    top: List[int]
    width: List[int]
    height: List[int]
    conf: List[int]
    text: List[str]

# ---------------------------------------------------------------------------- #


class TesseractOcrProvider(BaseOcrProvider):
    """
    This OCR provider uses Google's Tesseract to provide local OCR without
    and need for online processing. Make sure Tesseract is installed.
    """

    def run_ocr(
        self,
        images: List[Image.Image]
    ) -> OcrObject:
        """
        Use Google's Tesseract to apply OCR to an image and return an
        OcrResult pydantic model.
        """
        self.logger.debug("Processing image with Tesseract.")

        pages = []
        for page, image in enumerate(images):
            boxes = pytesseract.image_to_data(
                image=image,
                output_type=pytesseract.Output.DICT,
                lang="eng",  # todo
            )
            tesseract = TesseractResult(**boxes)

            blocks = self._convert_to_blocks(
                tesseract=tesseract,
                dimensions=(image.width, image.height)
            )

            ocr_page = OcrPage(
                page=page+1,
                blocks=blocks,
                dimensions=(image.width, image.height)
            )

            pages.append(ocr_page)

        return OcrObject(pages=pages)

    def _convert_to_blocks(
        self,
        tesseract: TesseractResult,
        dimensions: Tuple[int, int]
    ) -> List[OcrBlock]:
        blocks = []
        for index, text in enumerate(tesseract.text):
            if len(text) == 0:
                continue

            confidence: float | None = tesseract.conf[index]/100

            if confidence < 0:
                confidence = None

            coordinates = OcrCoordinates(
                left=round(tesseract.left[index] / dimensions[0] * 100.0, 5),
                top=round(tesseract.top[index] / dimensions[1] * 100.0, 5),
                width=round(tesseract.width[index] / dimensions[0] * 100.0, 5),
                height=round(
                    tesseract.height[index] / dimensions[1] * 100.0, 5)
            )

            block = OcrBlock(
                id=index,
                content=text,
                confidence=confidence,
                coordinates=coordinates
            )

            blocks.append(block)

        return blocks


# ---------------------------------------------------------------------------- #
