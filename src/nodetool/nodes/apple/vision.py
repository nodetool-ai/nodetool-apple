from __future__ import annotations

from enum import Enum

from pydantic import Field

import AppKit  # type: ignore
import Foundation  # type: ignore

try:
    import Vision  # type: ignore
except Exception:  # pragma: no cover
    Vision = None  # type: ignore

from nodetool.metadata.types import ImageRef, TextRef
from nodetool.workflows.base_node import BaseNode
from nodetool.workflows.processing_context import ProcessingContext


class OCRImage(BaseNode):
    """
    Extract text from an image using Apple's Vision framework (VNRecognizeTextRequest).
    vision, ocr, macos, automation

    Use cases:
    - Screenshot → OCR → summarize / classify
    - Read text from receipts, dialogs, error messages
    - Turn UI text into reminders/notes/messages
    """

    class RecognitionLevel(str, Enum):
        FAST = "fast"
        ACCURATE = "accurate"

    image: ImageRef = Field(description="Image to run OCR on")
    recognition_level: RecognitionLevel = Field(
        default=RecognitionLevel.ACCURATE,
        description="OCR speed/accuracy tradeoff",
    )
    languages: list[str] = Field(
        default_factory=list,
        description="Optional BCP-47 language codes (e.g. ['en-US','de-DE'])",
    )
    uses_language_correction: bool = Field(
        default=True, description="Enable language correction"
    )
    min_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Drop recognized strings below this confidence",
    )
    join_with: str = Field(
        default="\n",
        description="How to join recognized lines into the output text",
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["image", "recognition_level", "languages", "min_confidence"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return True

    @staticmethod
    def _nsdata_from_bytes(data: bytes) -> Foundation.NSData:  # type: ignore
        return Foundation.NSData.dataWithBytes_length_(data, len(data))  # type: ignore

    @staticmethod
    def _cgimage_from_bytes(data: bytes):
        nsdata = OCRImage._nsdata_from_bytes(data)
        image = AppKit.NSImage.alloc().initWithData_(nsdata)  # type: ignore
        if image is None:
            return None
        rect = Foundation.NSMakeRect(0, 0, 0, 0)  # type: ignore
        cg_image = image.CGImageForProposedRect_context_hints_(rect, None, None)  # type: ignore
        return cg_image

    async def process(self, context: ProcessingContext) -> TextRef:
        if Vision is None:  # pragma: no cover
            raise RuntimeError(
                "Vision framework is not available. Install `pyobjc-framework-Vision`."
            )

        image_bytes = await context.asset_to_bytes(self.image)
        cg_image = self._cgimage_from_bytes(image_bytes)
        if cg_image is None:
            raise RuntimeError("Failed to decode image for OCR")

        recognized: list[tuple[str, float]] = []

        def handler(request, error):  # type: ignore
            if error is not None:
                return
            results = request.results() or []  # type: ignore
            for obs in results:
                top = obs.topCandidates_(1)  # type: ignore
                if not top:
                    continue
                candidate = top[0]
                text = str(candidate.string())  # type: ignore
                confidence = float(candidate.confidence())  # type: ignore
                recognized.append((text, confidence))

        request = Vision.VNRecognizeTextRequest.alloc().initWithCompletionHandler_(  # type: ignore
            handler
        )

        request.setUsesLanguageCorrection_(self.uses_language_correction)  # type: ignore
        if self.languages:
            request.setRecognitionLanguages_(self.languages)  # type: ignore

        if self.recognition_level == self.RecognitionLevel.FAST:
            request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelFast)  # type: ignore
        else:
            request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)  # type: ignore

        req_handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(  # type: ignore
            cg_image, None
        )

        ok, error = req_handler.performRequests_error_([request], None)  # type: ignore
        if not ok:
            raise RuntimeError(f"OCR failed: {error}")

        lines = [t for (t, c) in recognized if c >= self.min_confidence]
        return await context.text_from_str(self.join_with.join(lines))
