from __future__ import annotations

from urllib.parse import urlparse

from pydantic import Field

import AppKit  # type: ignore

from nodetool.metadata.types import ImageRef, TextRef
from nodetool.workflows.base_node import BaseNode
from nodetool.workflows.processing_context import ProcessingContext


def _file_path_from_uri(uri: str) -> str | None:
    if not uri:
        return None
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return None
    return parsed.path


class GetClipboardText(BaseNode):
    """
    Read plain text from the macOS clipboard (NSPasteboard).
    clipboard, macos, automation, productivity

    Use cases:
    - “Copy → summarize → paste back” workflows
    - Use current selection as agent input
    - Lightweight handoff between apps and nodetool
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> TextRef:
        pasteboard = AppKit.NSPasteboard.generalPasteboard()  # type: ignore
        text = pasteboard.stringForType_(AppKit.NSPasteboardTypeString)  # type: ignore
        return await context.text_from_str(str(text) if text is not None else "")


class SetClipboardText(BaseNode):
    """
    Write plain text to the macOS clipboard (NSPasteboard).
    clipboard, macos, automation, productivity

    Use cases:
    - Put an LLM result on the clipboard for quick paste
    - Provide human-in-the-loop editing via copy/paste
    - Copy generated commands/snippets into other apps
    """

    text: str = Field(default="", description="Text to put on the clipboard")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["text"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        pasteboard = AppKit.NSPasteboard.generalPasteboard()  # type: ignore
        pasteboard.clearContents()  # type: ignore
        ok = pasteboard.setString_forType_(self.text, AppKit.NSPasteboardTypeString)  # type: ignore
        return bool(ok)


class GetClipboardImage(BaseNode):
    """
    Read an image from the macOS clipboard (NSPasteboard) and return it as an ImageRef.
    clipboard, macos, automation, media

    Use cases:
    - Copy an image/screenshot and run vision/OCR downstream
    - Quick “copy image → caption → paste alt text” flows
    - Route clipboard images into Notes/Files shortcuts
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> ImageRef:
        pasteboard = AppKit.NSPasteboard.generalPasteboard()  # type: ignore

        data = pasteboard.dataForType_(AppKit.NSPasteboardTypePNG)  # type: ignore
        if data is None:
            data = pasteboard.dataForType_(AppKit.NSPasteboardTypeTIFF)  # type: ignore

        if data is None:
            raise RuntimeError("No image data found on clipboard")

        image = AppKit.NSImage.alloc().initWithData_(data)  # type: ignore
        if image is None:
            raise RuntimeError("Failed to decode clipboard image")

        tiff = image.TIFFRepresentation()  # type: ignore
        rep = AppKit.NSBitmapImageRep.imageRepWithData_(tiff)  # type: ignore
        png = rep.representationUsingType_properties_(  # type: ignore
            AppKit.NSBitmapImageFileTypePNG, None  # type: ignore
        )
        if png is None:
            raise RuntimeError("Failed to convert clipboard image to PNG")

        return await context.image_from_bytes(bytes(png))


class SetClipboardImage(BaseNode):
    """
    Write an image to the macOS clipboard (NSPasteboard).
    clipboard, macos, automation, media

    Use cases:
    - Put a generated/processed image on the clipboard for quick paste
    - Copy charts/visualizations into Keynote/Slack/etc.
    - Human review loop: generate image → copy → paste somewhere
    """

    image: ImageRef = Field(description="Image to put on the clipboard")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["image"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        pasteboard = AppKit.NSPasteboard.generalPasteboard()  # type: ignore

        image_path = _file_path_from_uri(getattr(self.image, "uri", ""))
        if image_path:
            ns_image = AppKit.NSImage.alloc().initWithContentsOfFile_(image_path)  # type: ignore
        else:
            data = await context.asset_to_bytes(self.image)
            ns_image = AppKit.NSImage.alloc().initWithData_(data)  # type: ignore

        if ns_image is None:
            raise RuntimeError("Failed to decode image input")

        tiff = ns_image.TIFFRepresentation()  # type: ignore
        rep = AppKit.NSBitmapImageRep.imageRepWithData_(tiff)  # type: ignore
        png = rep.representationUsingType_properties_(  # type: ignore
            AppKit.NSBitmapImageFileTypePNG, None  # type: ignore
        )
        if png is None:
            raise RuntimeError("Failed to convert image to PNG")

        pasteboard.clearContents()  # type: ignore
        ok = pasteboard.setData_forType_(png, AppKit.NSPasteboardTypePNG)  # type: ignore
        return bool(ok)
