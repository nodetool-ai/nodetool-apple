"""
System-level macOS automation nodes for controlling volume, display, apps, and system settings.
"""

from __future__ import annotations

import subprocess
from typing import Any

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


class GetSystemVolume(BaseNode):
    """
    Get the current system audio output volume (0-100).
    system, volume, macos, automation

    Use cases:
    - Check volume before playing audio
    - Save and restore volume in workflows
    - Monitor volume level for accessibility
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> int:
        script = "output volume of (get volume settings)"
        out = _run_osascript(script)
        return int(out) if out.isdigit() else 0


class SetSystemVolume(BaseNode):
    """
    Set the system audio output volume (0-100).
    system, volume, macos, automation

    Use cases:
    - Mute system before TTS playback
    - Adjust volume for notifications
    - Automate volume for time-of-day workflows
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
        script = f"set volume output volume {self.volume}"
        _run_osascript(script)
        return True


class GetMuteState(BaseNode):
    """
    Check if the system audio is currently muted.
    system, volume, macos, automation

    Use cases:
    - Check mute state before playing audio
    - Save and restore mute state in workflows
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        script = "output muted of (get volume settings)"
        out = _run_osascript(script)
        return out.lower() == "true"


class SetMuteState(BaseNode):
    """
    Mute or unmute the system audio.
    system, volume, macos, automation

    Use cases:
    - Mute system during sensitive operations
    - Toggle mute for hands-free workflows
    """

    muted: bool = Field(
        default=True, description="Set to True to mute, False to unmute"
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["muted"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        script = f"set volume output muted {str(self.muted).lower()}"
        _run_osascript(script)
        return True


class GetDarkMode(BaseNode):
    """
    Check if macOS Dark Mode is currently enabled.
    system, appearance, macos, automation

    Use cases:
    - Sync workflow output colors with system theme
    - Conditional logic based on appearance mode
    - Accessibility-aware workflows
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        script = """
        tell application "System Events"
            tell appearance preferences
                return dark mode
            end tell
        end tell
        """
        out = _run_osascript(script)
        return out.lower() == "true"


class SetDarkMode(BaseNode):
    """
    Enable or disable macOS Dark Mode.
    system, appearance, macos, automation

    Use cases:
    - Toggle dark mode on schedule
    - Switch appearance for presentations
    - Sync appearance with external lighting
    """

    enabled: bool = Field(default=True, description="Enable dark mode")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["enabled"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        script = f"""
        tell application "System Events"
            tell appearance preferences
                set dark mode to {str(self.enabled).lower()}
            end tell
        end tell
        """
        _run_osascript(script)
        return True


class SleepDisplay(BaseNode):
    """
    Put the display to sleep (without sleeping the whole system).
    system, display, macos, automation

    Use cases:
    - Save power when running unattended workflows
    - Quick privacy screen for leaving desk
    - Power management automation
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        try:
            subprocess.run(
                ["pmset", "displaysleepnow"],
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to sleep display: {e.stderr}") from e


class GetBatteryStatus(BaseNode):
    """
    Get battery status information (percentage, charging state, time remaining).
    system, battery, macos, automation

    Use cases:
    - Conditional workflows based on battery level
    - Power-aware task scheduling
    - Battery monitoring and alerts
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> dict:
        try:
            result = subprocess.run(
                ["pmset", "-g", "batt"],
                check=True,
                capture_output=True,
                text=True,
            )
            output = result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get battery status: {e.stderr}") from e

        # Parse pmset output
        info: dict[str, Any] = {
            "percentage": 0,
            "is_charging": False,
            "is_on_ac": False,
            "time_remaining": "",
        }

        lines = output.strip().split("\n")
        for line in lines:
            if "AC Power" in line:
                info["is_on_ac"] = True
            if "%" in line:
                # Extract percentage
                import re

                match = re.search(r"(\d+)%", line)
                if match:
                    info["percentage"] = int(match.group(1))
                if "charging" in line.lower():
                    info["is_charging"] = True
                elif "discharging" in line.lower():
                    info["is_charging"] = False
                # Time remaining
                time_match = re.search(r"(\d+:\d+) remaining", line)
                if time_match:
                    info["time_remaining"] = time_match.group(1)

        return info


class ListRunningApplications(BaseNode):
    """
    List all currently running applications.
    system, applications, macos, automation

    Use cases:
    - Check if an app is running before sending commands
    - Monitor active applications for workflows
    - Application discovery for automation
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> list[str]:
        script = """
        tell application "System Events"
            set appNames to name of every process whose background only is false
            set AppleScript's text item delimiters to linefeed
            return appNames as text
        end tell
        """
        out = _run_osascript(script)
        return [app.strip() for app in out.split("\n") if app.strip()]


class OpenApplication(BaseNode):
    """
    Launch or bring to front a macOS application.
    system, applications, macos, automation

    Use cases:
    - Open apps as part of a workflow
    - Bring an app to foreground for user interaction
    - Launch specific tools before automation steps
    """

    app_name: str = Field(default="", description="Name of the application to open")
    activate: bool = Field(
        default=True, description="Bring the application to the foreground"
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["app_name", "activate"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        if not self.app_name.strip():
            raise ValueError("app_name is required")

        app_name = escape_for_applescript(self.app_name)
        activate_cmd = "activate" if self.activate else ""
        script = f"""
        tell application "{app_name}"
            {activate_cmd}
        end tell
        """
        _run_osascript(script)
        return True


class QuitApplication(BaseNode):
    """
    Quit a running macOS application.
    system, applications, macos, automation

    Use cases:
    - Clean up apps after workflow completion
    - Close apps before system sleep
    - Resource management automation
    """

    app_name: str = Field(default="", description="Name of the application to quit")
    save_changes: bool = Field(
        default=True, description="Prompt to save changes (if applicable)"
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["app_name", "save_changes"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        if not self.app_name.strip():
            raise ValueError("app_name is required")

        app_name = escape_for_applescript(self.app_name)
        saving = "yes" if self.save_changes else "no"
        script = f"""
        tell application "{app_name}"
            quit saving {saving}
        end tell
        """
        try:
            _run_osascript(script)
        except RuntimeError:
            # App might already be quit or not running
            pass
        return True


class GetFrontmostApplication(BaseNode):
    """
    Get the name of the currently frontmost (active) application.
    system, applications, macos, automation

    Use cases:
    - Context-aware workflows based on active app
    - Log which app user is working in
    - Conditional automation based on focus
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> str:
        script = """
        tell application "System Events"
            return name of first process whose frontmost is true
        end tell
        """
        return _run_osascript(script)


class EmptyTrash(BaseNode):
    """
    Empty the macOS Trash.
    system, finder, macos, automation

    Use cases:
    - Clean up after batch file operations
    - Scheduled maintenance workflows
    - Free disk space automation
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        script = """
        tell application "Finder"
            empty trash
        end tell
        """
        _run_osascript(script)
        return True
