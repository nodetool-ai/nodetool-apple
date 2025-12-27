"""
Text and language services nodes using macOS frameworks.
"""

from __future__ import annotations

import subprocess
from enum import Enum

from pydantic import Field

from nodetool.workflows.base_node import BaseNode
from nodetool.workflows.processing_context import ProcessingContext


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


class WordCount(BaseNode):
    """
    Count words, characters, lines, and paragraphs in text.
    text, statistics, macos, automation

    Use cases:
    - Validate content length constraints
    - Generate text statistics for reports
    - Content analysis workflows
    """

    text: str = Field(default="", description="Text to analyze")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["text"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return True

    async def process(self, context: ProcessingContext) -> dict:
        text = self.text

        # Count characters (with and without spaces)
        chars_with_spaces = len(text)
        chars_without_spaces = len(text.replace(" ", "").replace("\t", ""))

        # Count words
        words = len(text.split())

        # Count lines
        lines = len(text.splitlines()) if text else 0

        # Count paragraphs (separated by blank lines)
        paragraphs = len([p for p in text.split("\n\n") if p.strip()])

        return {
            "characters": chars_with_spaces,
            "characters_no_spaces": chars_without_spaces,
            "words": words,
            "lines": lines,
            "paragraphs": paragraphs,
        }


class ConvertTextCase(BaseNode):
    """
    Convert text to different cases (upper, lower, title, sentence).
    text, case, macos, automation

    Use cases:
    - Normalize text formatting
    - Prepare text for display
    - Standardize input case
    """

    class TextCase(str, Enum):
        UPPER = "upper"
        LOWER = "lower"
        TITLE = "title"
        SENTENCE = "sentence"
        CAPITALIZE = "capitalize"

    text: str = Field(default="", description="Text to convert")
    case: TextCase = Field(default=TextCase.LOWER, description="Target case")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["text", "case"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return True

    async def process(self, context: ProcessingContext) -> str:
        if not self.text:
            return ""

        if self.case == self.TextCase.UPPER:
            return self.text.upper()
        elif self.case == self.TextCase.LOWER:
            return self.text.lower()
        elif self.case == self.TextCase.TITLE:
            return self.text.title()
        elif self.case == self.TextCase.CAPITALIZE:
            return self.text.capitalize()
        elif self.case == self.TextCase.SENTENCE:
            # Capitalize first letter of each sentence
            import re

            result = re.sub(
                r"(^|[.!?]\s+)([a-z])",
                lambda m: m.group(1) + m.group(2).upper(),
                self.text.lower(),
            )
            return result
        return self.text


class ExtractURLs(BaseNode):
    """
    Extract all URLs from text.
    text, urls, macos, automation

    Use cases:
    - Parse links from email/document content
    - Build link collections from text
    - URL validation workflows
    """

    text: str = Field(default="", description="Text to extract URLs from")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["text"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return True

    async def process(self, context: ProcessingContext) -> list[str]:
        if not self.text:
            return []

        import re

        # URL pattern
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, self.text)
        # Remove trailing punctuation that might have been captured
        cleaned = []
        for url in urls:
            url = url.rstrip(".,;:!?)")
            if url not in cleaned:
                cleaned.append(url)
        return cleaned


class ExtractEmails(BaseNode):
    """
    Extract all email addresses from text.
    text, email, macos, automation

    Use cases:
    - Parse contacts from documents
    - Extract recipients from content
    - Email validation workflows
    """

    text: str = Field(default="", description="Text to extract email addresses from")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["text"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return True

    async def process(self, context: ProcessingContext) -> list[str]:
        if not self.text:
            return []

        import re

        # Email pattern
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        emails = re.findall(email_pattern, self.text)
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for email in emails:
            lower = email.lower()
            if lower not in seen:
                seen.add(lower)
                unique.append(email)
        return unique
