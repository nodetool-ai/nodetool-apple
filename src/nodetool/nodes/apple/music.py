"""
Apple Music app integration nodes for media playback control.
"""

from __future__ import annotations

import subprocess
from enum import Enum

from pydantic import Field

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


class GetCurrentTrack(BaseNode):
    """
    Get information about the currently playing track in Apple Music.
    music, media, macos, automation

    Use cases:
    - Log what's playing during workflow execution
    - Create "now playing" notifications
    - Build music-aware workflows
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> dict:
        script = """
        tell application "Music"
            if player state is not stopped then
                set trackName to name of current track
                set trackArtist to artist of current track
                set trackAlbum to album of current track
                set trackDuration to duration of current track
                set trackPosition to player position
                return trackName & "\\n" & trackArtist & "\\n" & trackAlbum & "\\n" & trackDuration & "\\n" & trackPosition
            else
                return ""
            end if
        end tell
        """
        out = _run_osascript(script)
        if not out:
            return {
                "name": "",
                "artist": "",
                "album": "",
                "duration": 0,
                "position": 0,
                "is_playing": False,
            }

        parts = out.split("\n")
        return {
            "name": parts[0] if len(parts) > 0 else "",
            "artist": parts[1] if len(parts) > 1 else "",
            "album": parts[2] if len(parts) > 2 else "",
            "duration": float(parts[3]) if len(parts) > 3 and parts[3] else 0,
            "position": float(parts[4]) if len(parts) > 4 and parts[4] else 0,
            "is_playing": True,
        }


class PlayerState(str, Enum):
    """Music player states."""

    PLAY = "play"
    PAUSE = "pause"
    STOP = "stop"
    NEXT = "next"
    PREVIOUS = "previous"


class MusicControl(BaseNode):
    """
    Control Apple Music playback (play, pause, stop, next, previous).
    music, media, macos, automation

    Use cases:
    - Pause music during speech synthesis
    - Create playlist automation workflows
    - Remote control music from mobile workflows
    """

    action: PlayerState = Field(
        default=PlayerState.PLAY, description="Playback action to perform"
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["action"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        action_map = {
            PlayerState.PLAY: "play",
            PlayerState.PAUSE: "pause",
            PlayerState.STOP: "stop",
            PlayerState.NEXT: "next track",
            PlayerState.PREVIOUS: "previous track",
        }
        action = action_map[self.action]
        script = f"""
        tell application "Music"
            {action}
        end tell
        """
        _run_osascript(script)
        return True


class GetMusicPlayerState(BaseNode):
    """
    Get the current player state (playing, paused, stopped) of Apple Music.
    music, media, macos, automation

    Use cases:
    - Check if music is playing before starting TTS
    - Resume music after pause in workflow
    - Monitor playback status
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> str:
        script = """
        tell application "Music"
            return player state as string
        end tell
        """
        return _run_osascript(script)


class SetMusicVolume(BaseNode):
    """
    Set the Apple Music app volume (independent of system volume).
    music, media, macos, automation

    Use cases:
    - Lower music volume before TTS
    - Fade music volume in workflows
    - Per-app volume control
    """

    volume: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Volume level (0-100)",
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["volume"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        script = f"""
        tell application "Music"
            set sound volume to {self.volume}
        end tell
        """
        _run_osascript(script)
        return True


class GetMusicVolume(BaseNode):
    """
    Get the current Apple Music app volume.
    music, media, macos, automation

    Use cases:
    - Save volume before adjustment
    - Monitor music volume levels
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> int:
        script = """
        tell application "Music"
            return sound volume
        end tell
        """
        out = _run_osascript(script)
        return int(out) if out.isdigit() else 0


class SearchMusic(BaseNode):
    """
    Search for tracks in Apple Music library.
    music, search, macos, automation

    Use cases:
    - Find songs to play by name
    - Build music discovery workflows
    - Create dynamic playlists
    """

    query: str = Field(default="", description="Search query for track name/artist")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results to return")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["query", "limit"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return True

    async def process(self, context: ProcessingContext) -> list[dict]:
        if not self.query.strip():
            return []

        from nodetool.nodes.apple.notes import escape_for_applescript

        query = escape_for_applescript(self.query)
        script = f"""
        tell application "Music"
            set foundTracks to (search library playlist 1 for "{query}")
            set output to ""
            set counter to 0
            repeat with t in foundTracks
                if counter >= {self.limit} then exit repeat
                set output to output & name of t & "||" & artist of t & "||" & album of t & "||" & id of t & linefeed
                set counter to counter + 1
            end repeat
            return output
        end tell
        """
        out = _run_osascript(script)
        if not out:
            return []

        results = []
        for line in out.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("||")
            if len(parts) >= 4:
                results.append(
                    {
                        "name": parts[0],
                        "artist": parts[1],
                        "album": parts[2],
                        "id": parts[3],
                    }
                )
        return results


class PlayTrackById(BaseNode):
    """
    Play a specific track by its Music library ID.
    music, media, macos, automation

    Use cases:
    - Play a specific song from search results
    - Create precise playlist automations
    - Resume a specific track
    """

    track_id: str = Field(default="", description="Music track ID to play")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["track_id"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        if not self.track_id.strip():
            raise ValueError("track_id is required")

        from nodetool.nodes.apple.notes import escape_for_applescript

        track_id = escape_for_applescript(self.track_id)
        script = f"""
        tell application "Music"
            play (first track whose id is "{track_id}")
        end tell
        """
        _run_osascript(script)
        return True
