import subprocess

from pydantic import Field

from nodetool.nodes.apple.notes import escape_for_applescript
from nodetool.workflows.base_node import BaseNode
from nodetool.workflows.processing_context import ProcessingContext


class PostNotification(BaseNode):
    """
    Post a macOS Notification Center notification via AppleScript (`display notification`).
    notifications, macos, automation, productivity

    Use cases:
    - Notify when a workflow finishes
    - Surface an agent’s result without switching apps
    - Provide lightweight progress/status updates
    """

    title: str = Field(default="Nodetool", description="Notification title")
    subtitle: str = Field(default="", description="Notification subtitle")
    message: str = Field(default="", description="Notification message body")
    sound_name: str = Field(
        default="",
        description="Optional sound name (e.g. 'Glass'); empty means no sound",
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["title", "message"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        title = escape_for_applescript(self.title)
        subtitle = escape_for_applescript(self.subtitle)
        message = escape_for_applescript(self.message)
        sound_name = escape_for_applescript(self.sound_name)

        parts = [f'display notification "{message}" with title "{title}"']
        if subtitle:
            parts.append(f'subtitle "{subtitle}"')
        if sound_name:
            parts.append(f'sound name "{sound_name}"')

        script = " ".join(parts)

        try:
            subprocess.run(
                ["osascript", "-e", script], check=True, capture_output=True, text=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to post notification: {e.stderr}") from e

        return True
