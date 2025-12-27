"""
macOS Photos app integration nodes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from pydantic import Field

from nodetool.nodes.apple.notes import escape_for_applescript
from nodetool.metadata.types import ImageRef
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


class ImportToPhotos(BaseNode):
    """
    Import an image into Apple Photos.
    photos, media, macos, automation

    Use cases:
    - Save generated images to Photos library
    - Archive processed images
    - Organize workflow outputs in Photos albums
    """

    image: ImageRef = Field(default=ImageRef(), description="Image to import")
    skip_duplicate: bool = Field(
        default=True, description="Skip if a duplicate exists in Photos"
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["image"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        # Save image to a temp file
        import tempfile

        image_bytes = await context.asset_to_bytes(self.image)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(image_bytes)
            temp_path = f.name

        try:
            posix_path = escape_for_applescript(temp_path)
            skip_dup = "yes" if self.skip_duplicate else "no"
            script = f"""
            tell application "Photos"
                import POSIX file "{posix_path}" skip check duplicates {skip_dup}
            end tell
            """
            _run_osascript(script)
            return True
        finally:
            Path(temp_path).unlink(missing_ok=True)


class GetPhotosAlbums(BaseNode):
    """
    List all albums in Apple Photos.
    photos, albums, macos, automation

    Use cases:
    - Discover albums for import targets
    - List albums for user selection
    - Build album-aware workflows
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> list[str]:
        script = """
        tell application "Photos"
            set albumNames to name of every album
            set AppleScript's text item delimiters to linefeed
            return albumNames as text
        end tell
        """
        out = _run_osascript(script)
        if not out:
            return []
        return [a.strip() for a in out.split("\n") if a.strip()]


class GetRecentPhotos(BaseNode):
    """
    Get file paths to the most recent photos in Photos library.
    photos, media, macos, automation

    Use cases:
    - Process latest photos in workflows
    - Quick access to recent camera imports
    - Photo-based automation triggers

    Note: Photos must be exported to access actual files.
    """

    limit: int = Field(default=10, ge=1, le=100, description="Number of recent photos")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["limit"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> list[dict]:
        script = f"""
        tell application "Photos"
            set recentPhotos to media items 1 thru {self.limit}
            set output to ""
            repeat with p in recentPhotos
                set pName to filename of p
                set pDate to date of p as string
                set pId to id of p
                set output to output & pName & "|||" & pDate & "|||" & pId & linefeed
            end repeat
            return output
        end tell
        """
        out = _run_osascript(script)
        if not out:
            return []

        photos = []
        for line in out.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("|||")
            if len(parts) >= 3:
                photos.append(
                    {
                        "filename": parts[0],
                        "date": parts[1],
                        "id": parts[2],
                    }
                )
        return photos


class CreatePhotosAlbum(BaseNode):
    """
    Create a new album in Apple Photos.
    photos, albums, macos, automation

    Use cases:
    - Organize workflow outputs into new albums
    - Set up album structure for imports
    - Create project-specific photo collections
    """

    name: str = Field(default="", description="Name for the new album")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["name"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        if not self.name.strip():
            raise ValueError("name is required")

        album_name = escape_for_applescript(self.name)
        script = f"""
        tell application "Photos"
            make new album named "{album_name}"
        end tell
        """
        _run_osascript(script)
        return True
