"""
Finder integration nodes for file management and navigation.
"""

from __future__ import annotations

import subprocess
from enum import Enum
from pathlib import Path

from pydantic import Field

from nodetool.nodes.apple.notes import escape_for_applescript
from nodetool.workflows.base_node import BaseNode
from nodetool.workflows.processing_context import ProcessingContext


def _run_osascript(script: str) -> str:
    """Run an AppleScript and return stdout."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script], check=True, capture_output=True, text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"AppleScript failed: {e.stderr}") from e


class GetSelectedFinderItems(BaseNode):
    """
    Get the paths of currently selected items in Finder.
    finder, files, macos, automation

    Use cases:
    - Process user-selected files in workflows
    - Get context for "right-click" style automations
    - Build on user's current file selection
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> list[str]:
        script = """
        tell application "Finder"
            set selectedItems to selection
            set pathList to {}
            repeat with anItem in selectedItems
                set end of pathList to POSIX path of (anItem as alias)
            end repeat
            set AppleScript's text item delimiters to linefeed
            return pathList as text
        end tell
        """
        out = _run_osascript(script)
        if not out:
            return []
        return [p.strip() for p in out.split("\n") if p.strip()]


class GetFrontFinderWindow(BaseNode):
    """
    Get the path of the frontmost Finder window's folder.
    finder, navigation, macos, automation

    Use cases:
    - Know user's current working directory in Finder
    - Context-aware file operations
    - Save files to the currently viewed folder
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> str:
        script = """
        tell application "Finder"
            if not (exists front window) then return ""
            return POSIX path of (target of front window as alias)
        end tell
        """
        return _run_osascript(script)


class RevealInFinder(BaseNode):
    """
    Reveal a file or folder in Finder (opens containing folder and selects item).
    finder, files, macos, automation

    Use cases:
    - Show user where a processed file was saved
    - Navigate to workflow output location
    - Highlight important files for review
    """

    path: str = Field(default="", description="Path to the file or folder to reveal")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["path"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        if not self.path.strip():
            raise ValueError("path is required")

        posix_path = escape_for_applescript(self.path)
        script = f"""
        tell application "Finder"
            reveal POSIX file "{posix_path}"
            activate
        end tell
        """
        _run_osascript(script)
        return True


class MoveToTrash(BaseNode):
    """
    Move a file or folder to the Trash.
    finder, files, macos, automation

    Use cases:
    - Clean up temporary files after processing
    - Safe deletion with recovery option
    - Batch file cleanup workflows
    """

    path: str = Field(default="", description="Path to the file or folder to trash")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["path"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        if not self.path.strip():
            raise ValueError("path is required")

        posix_path = escape_for_applescript(self.path)
        script = f"""
        tell application "Finder"
            delete POSIX file "{posix_path}"
        end tell
        """
        _run_osascript(script)
        return True


class FinderTag(str, Enum):
    """Standard Finder tag colors."""

    NONE = "0"
    GRAY = "1"
    GREEN = "2"
    PURPLE = "3"
    BLUE = "4"
    YELLOW = "5"
    RED = "6"
    ORANGE = "7"


class SetFinderTag(BaseNode):
    """
    Set a color tag on a file or folder in Finder.
    finder, tags, macos, automation

    Use cases:
    - Mark processed files for easy identification
    - Categorize files by workflow status
    - Visual organization of workflow outputs
    """

    path: str = Field(default="", description="Path to the file or folder")
    tag: FinderTag = Field(default=FinderTag.NONE, description="Tag color to apply")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["path", "tag"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        if not self.path.strip():
            raise ValueError("path is required")

        # Use xattr to set the color label
        try:
            # macOS uses com.apple.FinderInfo xattr for tags
            # This uses the Finder AppleScript approach which is more reliable
            posix_path = escape_for_applescript(self.path)
            script = f"""
            tell application "Finder"
                set theFile to POSIX file "{posix_path}" as alias
                set label index of theFile to {self.tag.value}
            end tell
            """
            _run_osascript(script)
            return True
        except RuntimeError as e:
            raise RuntimeError(f"Failed to set Finder tag: {e}") from e


class GetFinderTag(BaseNode):
    """
    Get the color tag of a file or folder in Finder.
    finder, tags, macos, automation

    Use cases:
    - Check if a file has been processed (tagged)
    - Filter files by tag status
    - Read existing organization for workflows
    """

    path: str = Field(default="", description="Path to the file or folder")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["path"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> int:
        if not self.path.strip():
            raise ValueError("path is required")

        posix_path = escape_for_applescript(self.path)
        script = f"""
        tell application "Finder"
            set theFile to POSIX file "{posix_path}" as alias
            return label index of theFile
        end tell
        """
        out = _run_osascript(script)
        return int(out) if out.isdigit() else 0


class OpenFinderWindow(BaseNode):
    """
    Open a new Finder window at the specified path.
    finder, navigation, macos, automation

    Use cases:
    - Open folder for user review
    - Navigate to workflow output directory
    - Set up workspace windows
    """

    path: str = Field(
        default="~", description="Path to open (defaults to home directory)"
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["path"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        expanded = str(Path(self.path).expanduser())
        posix_path = escape_for_applescript(expanded)
        script = f"""
        tell application "Finder"
            make new Finder window to POSIX file "{posix_path}"
            activate
        end tell
        """
        _run_osascript(script)
        return True


class GetDesktopPath(BaseNode):
    """
    Get the path to the user's Desktop folder.
    finder, paths, macos, automation

    Use cases:
    - Save workflow outputs to Desktop for easy access
    - Reference common user folders
    - Cross-user compatible path resolution
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return True

    async def process(self, context: ProcessingContext) -> str:
        return str(Path.home() / "Desktop")


class GetDownloadsPath(BaseNode):
    """
    Get the path to the user's Downloads folder.
    finder, paths, macos, automation

    Use cases:
    - Process newly downloaded files
    - Monitor downloads folder for automation triggers
    - Save workflow outputs to Downloads
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return True

    async def process(self, context: ProcessingContext) -> str:
        return str(Path.home() / "Downloads")


class GetDocumentsPath(BaseNode):
    """
    Get the path to the user's Documents folder.
    finder, paths, macos, automation

    Use cases:
    - Save important workflow outputs to Documents
    - Access user documents for processing
    - Cross-user compatible path resolution
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return True

    async def process(self, context: ProcessingContext) -> str:
        return str(Path.home() / "Documents")
