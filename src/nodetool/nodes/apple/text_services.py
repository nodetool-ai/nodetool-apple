"""
Text and language services nodes using macOS frameworks.
"""

from __future__ import annotations

from enum import Enum

from nodetool.workflows.base_node import BaseNode
from nodetool.workflows.processing_context import ProcessingContext
from pydantic import Field


class DetectLanguage(BaseNode):
    """
    Detect the dominant language of a text using CoreFoundation.
    language, text, macos, automation

    Use cases:
    - Route text to appropriate translation services
    - Language-aware content processing
    - Multi-language workflow branching
    """

    text: str = Field(default="", description="Text to analyze for language")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["text"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return True

    async def process(self, context: ProcessingContext) -> str:
        if not self.text.strip():
            return ""

        try:
            import CoreFoundation  # type: ignore

            tokenizer = CoreFoundation.CFStringTokenizerCreate(  # type: ignore
                None,
                self.text,
                (0, len(self.text)),
                CoreFoundation.kCFStringTokenizerUnitWord,  # type: ignore
                None,
            )
            lang = CoreFoundation.CFStringTokenizerCopyBestStringLanguage(  # type: ignore
                self.text, (0, min(len(self.text), 500))
            )
            return str(lang) if lang else ""
        except Exception:
            return ""


class SpellCheck(BaseNode):
    """
    Check spelling in text using macOS spell checker.
    spelling, text, macos, automation

    Use cases:
    - Validate text before sending/publishing
    - Find typos in workflow inputs
    - Quality control for generated content
    """

    text: str = Field(default="", description="Text to spell check")
    language: str = Field(
        default="en", description="Language code for spell checking (e.g., 'en', 'de')"
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["text", "language"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return True

    async def process(self, context: ProcessingContext) -> list[dict]:
        if not self.text.strip():
            return []

        try:
            import AppKit  # type: ignore

            checker = AppKit.NSSpellChecker.sharedSpellChecker()  # type: ignore
            checker.setLanguage_(self.language)  # type: ignore

            text = self.text
            start = 0
            misspellings = []

            while start < len(text):
                range_info = checker.checkSpellingOfString_startingAt_(text, start)  # type: ignore
                if range_info.length == 0:
                    break

                word = text[
                    range_info.location : range_info.location + range_info.length
                ]
                guesses = checker.guessesForWordRange_inString_language_inSpellDocumentWithTag_(  # type: ignore
                    range_info, text, self.language, 0
                )
                suggestions = list(guesses) if guesses else []

                misspellings.append(
                    {
                        "word": word,
                        "position": range_info.location,
                        "suggestions": suggestions[:5],  # Limit suggestions
                    }
                )

                start = range_info.location + range_info.length

            return misspellings
        except Exception as e:
            raise RuntimeError(f"Spell check failed: {e}") from e
