"""
Apple Mail integration nodes for email automation.
"""

from __future__ import annotations

import subprocess

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


class CreateMailDraft(BaseNode):
    """
    Create a new email draft in Apple Mail (does not send).
    mail, email, macos, automation

    Use cases:
    - Prepare emails for human review before sending
    - Create bulk email drafts from workflow data
    - Set up scheduled email preparation
    """

    to: str = Field(
        default="", description="Recipient email address(es), comma-separated"
    )
    subject: str = Field(default="", description="Email subject line")
    body: str = Field(default="", description="Email body content")
    cc: str = Field(default="", description="CC recipients, comma-separated")
    bcc: str = Field(default="", description="BCC recipients, comma-separated")
    visible: bool = Field(default=True, description="Show the draft window to the user")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["to", "subject", "body"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        to_addr = escape_for_applescript(self.to)
        subject = escape_for_applescript(self.subject)
        body = escape_for_applescript(self.body)

        # Build recipient properties
        recipient_commands = []
        if self.to.strip():
            for addr in self.to.split(","):
                addr = addr.strip()
                if addr:
                    addr_escaped = escape_for_applescript(addr)
                    recipient_commands.append(
                        f'make new to recipient at end of to recipients with properties {{address:"{addr_escaped}"}}'
                    )

        if self.cc.strip():
            for addr in self.cc.split(","):
                addr = addr.strip()
                if addr:
                    addr_escaped = escape_for_applescript(addr)
                    recipient_commands.append(
                        f'make new cc recipient at end of cc recipients with properties {{address:"{addr_escaped}"}}'
                    )

        if self.bcc.strip():
            for addr in self.bcc.split(","):
                addr = addr.strip()
                if addr:
                    addr_escaped = escape_for_applescript(addr)
                    recipient_commands.append(
                        f'make new bcc recipient at end of bcc recipients with properties {{address:"{addr_escaped}"}}'
                    )

        recipient_script = "\n                ".join(recipient_commands)
        visible_str = "true" if self.visible else "false"

        script = f"""
        tell application "Mail"
            set newMessage to make new outgoing message with properties {{subject:"{subject}", content:"{body}", visible:{visible_str}}}
            tell newMessage
                {recipient_script}
            end tell
        end tell
        """
        _run_osascript(script)
        return True


class GetSelectedMailMessages(BaseNode):
    """
    Get information about currently selected messages in Mail.
    mail, email, macos, automation

    Use cases:
    - Process user-selected emails in workflows
    - Extract content from selected emails
    - Build email-based automation triggers
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> list[dict]:
        script = """
        tell application "Mail"
            set selectedMessages to selection
            set output to ""
            repeat with msg in selectedMessages
                set msgSubject to subject of msg
                set msgSender to sender of msg
                set msgDate to date sent of msg as string
                set msgContent to content of msg
                -- Use a delimiter that's unlikely in email content
                set output to output & msgSubject & "|||" & msgSender & "|||" & msgDate & "|||" & msgContent & "###MSG###"
            end repeat
            return output
        end tell
        """
        out = _run_osascript(script)
        if not out:
            return []

        messages = []
        for msg_str in out.split("###MSG###"):
            if not msg_str.strip():
                continue
            parts = msg_str.split("|||")
            if len(parts) >= 4:
                messages.append(
                    {
                        "subject": parts[0],
                        "sender": parts[1],
                        "date": parts[2],
                        "content": parts[3],
                    }
                )
        return messages


class GetUnreadMailCount(BaseNode):
    """
    Get the count of unread emails in Mail.
    mail, email, macos, automation

    Use cases:
    - Check for new emails in workflows
    - Trigger actions based on unread count
    - Monitor inbox status
    """

    mailbox: str = Field(
        default="INBOX", description="Mailbox name to check (default: INBOX)"
    )
    account: str = Field(
        default="", description="Account name (optional, uses first if empty)"
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["mailbox", "account"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> int:
        if self.account.strip():
            account = escape_for_applescript(self.account)
            mailbox = escape_for_applescript(self.mailbox)
            script = f"""
            tell application "Mail"
                return unread count of mailbox "{mailbox}" of account "{account}"
            end tell
            """
        else:
            script = """
            tell application "Mail"
                return unread count of inbox
            end tell
            """
        out = _run_osascript(script)
        return int(out) if out.isdigit() else 0


class ListMailAccounts(BaseNode):
    """
    List all configured email accounts in Mail.
    mail, email, macos, automation

    Use cases:
    - Discover available accounts for sending
    - Select account for email operations
    - Multi-account email workflows
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> list[str]:
        script = """
        tell application "Mail"
            set accountNames to name of every account
            set AppleScript's text item delimiters to linefeed
            return accountNames as text
        end tell
        """
        out = _run_osascript(script)
        if not out:
            return []
        return [a.strip() for a in out.split("\n") if a.strip()]


class SendMail(BaseNode):
    """
    Send an email via Apple Mail.
    mail, email, macos, automation

    Use cases:
    - Send automated notifications
    - Complete email workflows
    - Alert on workflow completion

    Note: This will actually send an email. Use CreateMailDraft for drafts.
    """

    to: str = Field(
        default="", description="Recipient email address(es), comma-separated"
    )
    subject: str = Field(default="", description="Email subject line")
    body: str = Field(default="", description="Email body content")
    from_account: str = Field(
        default="", description="Account to send from (optional, uses default)"
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["to", "subject", "body"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        if not self.to.strip():
            raise ValueError("to address is required")

        subject = escape_for_applescript(self.subject)
        body = escape_for_applescript(self.body)

        # Build recipient list
        recipient_commands = []
        for addr in self.to.split(","):
            addr = addr.strip()
            if addr:
                addr_escaped = escape_for_applescript(addr)
                recipient_commands.append(
                    f'make new to recipient at end of to recipients with properties {{address:"{addr_escaped}"}}'
                )

        recipient_script = "\n                ".join(recipient_commands)

        script = f"""
        tell application "Mail"
            set newMessage to make new outgoing message with properties {{subject:"{subject}", content:"{body}", visible:false}}
            tell newMessage
                {recipient_script}
            end tell
            send newMessage
        end tell
        """
        _run_osascript(script)
        return True
