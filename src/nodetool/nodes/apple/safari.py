import subprocess

from pydantic import Field

from nodetool.nodes.apple.notes import escape_for_applescript
from nodetool.metadata.types import TextRef
from nodetool.workflows.base_node import BaseNode
from nodetool.workflows.processing_context import ProcessingContext


def _run_osascript(script: str) -> str:
    try:
        result = subprocess.run(
            ["osascript", "-e", script], check=True, capture_output=True, text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"AppleScript failed: {e.stderr}") from e


class GetFrontSafariTab(BaseNode):
    """
    Get URL/title of the front tab in Safari via AppleScript.
    safari, browser, macos, automation

    Use cases:
    - Summarize what you're currently reading
    - Save current page into Notes/Reminders
    - Route the active URL into download/scrape workflows
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> dict:
        script = """
        tell application "Safari"
            if not (exists front document) then return ""
            set t to front tab of front window
            set theURL to URL of t
            set theTitle to name of t
            return theURL & "\\n" & theTitle
        end tell
        """
        out = _run_osascript(script)
        if not out:
            return {"url": "", "title": ""}
        parts = out.split("\n", 1)
        return {
            "url": parts[0].strip(),
            "title": (parts[1].strip() if len(parts) > 1 else ""),
        }


class OpenSafariURL(BaseNode):
    """
    Open a URL in Safari via AppleScript.
    safari, browser, macos, automation

    Use cases:
    - Open links from an agent step
    - Jump to a search result for human verification
    - Bring Safari to the foreground on demand
    """

    url: str = Field(default="", description="URL to open in Safari")
    activate: bool = Field(default=True, description="Bring Safari to the foreground")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["url", "activate"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        url = escape_for_applescript(self.url)
        script = f"""
        tell application "Safari"
            open location "{url}"
            {"activate" if self.activate else ""}
        end tell
        """
        _run_osascript(script)
        return True


class SafariSelectionText(BaseNode):
    """
    Read the current text selection from the front Safari tab (via injected JavaScript).
    safari, browser, macos, automation

    Use cases:
    - Copy a highlighted passage into an LLM prompt
    - Turn selected text into a note/task
    - Summarize just the selected section of a page
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> TextRef:
        js = "window.getSelection ? window.getSelection().toString() : ''"
        script = f"""
        tell application "Safari"
            if not (exists front document) then return ""
            set t to front tab of front window
            return do JavaScript "{escape_for_applescript(js)}" in t
        end tell
        """
        out = _run_osascript(script)
        return await context.text_from_str(out)


class SafariPageText(BaseNode):
    """
    Extract visible page text from the front Safari tab (via injected JavaScript).
    safari, browser, macos, automation

    Use cases:
    - Summarize an article without copy/paste
    - Feed page content into retrieval/notes pipelines
    - Create “reading assistant” workflows
    """

    max_chars: int = Field(
        default=50_000, ge=0, description="Truncate output to this many characters"
    )
    prefer_article: bool = Field(
        default=True, description="Prefer <article> text when present"
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["max_chars", "prefer_article"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> TextRef:
        if self.prefer_article:
            js = "(document.querySelector('article')?.innerText || document.body?.innerText || '')"
        else:
            js = "(document.body?.innerText || '')"

        script = f"""
        tell application "Safari"
            if not (exists front document) then return ""
            set t to front tab of front window
            return do JavaScript "{escape_for_applescript(js)}" in t
        end tell
        """
        out = _run_osascript(script)
        if self.max_chars and len(out) > self.max_chars:
            out = out[: self.max_chars]
        return await context.text_from_str(out)
