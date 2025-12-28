import subprocess
from pydantic import Field
from pathlib import Path
from nodetool.workflows.base_node import BaseNode
from nodetool.workflows.processing_context import ProcessingContext
from nodetool.metadata.types import TextRef
from nodetool.nodes.apple.notes import escape_for_applescript


def _run_osascript(script: str) -> str:
    """Run an AppleScript and return stdout."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script], check=True, capture_output=True, text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"AppleScript failed: {e.stderr}") from e


class SendMessage(BaseNode):
    """
    Send messages using macOS Messages.app via AppleScript
    messages, imessage, automation, macos, communication

    Use cases:
    - Send automated notifications via iMessage
    - Integrate messaging into workflows
    - Send workflow results to yourself or others
    """

    recipient: str = Field(
        default="",
        description="Phone number, email, or contact name to send message to",
    )
    text: str = Field(default="", description="Message content to send")

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        if not self.recipient.strip():
            raise ValueError("Recipient is required")
        if not self.text.strip():
            raise ValueError("Message text is required")

        text_content = escape_for_applescript(self.text)
        recipient = escape_for_applescript(self.recipient)

        script = f"""
        tell application "Messages"
            set targetService to 1st service whose service type = iMessage
            set targetBuddy to buddy "{recipient}" of targetService
            send "{text_content}" to targetBuddy
        end tell
        """
        _run_osascript(script)
        return True


class GetRecentMessages(BaseNode):
    """
    Get recent messages from a specific conversation in Messages.app.
    messages, imessage, automation, macos, communication

    Use cases:
    - Read recent conversation history
    - Monitor messages from a specific contact
    - Extract message data for processing
    """

    participant: str = Field(
        default="",
        description="Phone number, email, or contact name to get messages from",
    )
    limit: int = Field(
        default=20,
        description="Maximum number of messages to retrieve",
        ge=1,
        le=100,
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["participant", "limit"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> list[dict]:
        participant = escape_for_applescript(self.participant)

        script = f"""
        tell application "Messages"
            set output to ""
            set msgCount to 0
            set maxMsgs to {self.limit}
            
            try
                set targetChat to 1st chat whose participants contains buddy "{participant}"
                set allMessages to messages of targetChat
                
                repeat with msg in allMessages
                    if msgCount >= maxMsgs then exit repeat
                    
                    try
                        set msgText to text of msg
                        set msgSender to handle of sender of msg
                        set msgDate to date sent of msg as string
                        set msgIsFromMe to "false"
                        if sender of msg is me then set msgIsFromMe to "true"
                        
                        set output to output & msgText & "|||" & msgSender & "|||" & msgDate & "|||" & msgIsFromMe & "###MSG###"
                        set msgCount to msgCount + 1
                    end try
                end repeat
            on error errMsg
                return "ERROR:" & errMsg
            end try
            
            return output
        end tell
        """

        out = _run_osascript(script)
        if not out or out.startswith("ERROR:"):
            return []

        messages = []
        for msg_str in out.split("###MSG###"):
            if not msg_str.strip():
                continue
            parts = msg_str.split("|||")
            if len(parts) >= 4:
                messages.append(
                    {
                        "text": parts[0],
                        "sender": parts[1],
                        "date": parts[2],
                        "is_from_me": parts[3] == "true",
                    }
                )
        return messages


class ListConversations(BaseNode):
    """
    List all chat conversations in Messages.app.
    messages, imessage, automation, macos, communication

    Use cases:
    - Discover available conversations
    - Get list of contacts you've messaged
    - Find conversation IDs for further processing
    """

    limit: int = Field(
        default=50,
        description="Maximum number of conversations to retrieve",
        ge=1,
        le=200,
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["limit"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> list[dict]:
        script = f"""
        tell application "Messages"
            set output to ""
            set chatCount to 0
            set maxChats to {self.limit}
            
            try
                repeat with c in chats
                    if chatCount >= maxChats then exit repeat
                    
                    try
                        set chatName to name of c
                        set chatId to id of c
                        
                        -- Get participant handles
                        set participantList to ""
                        repeat with p in participants of c
                            set participantList to participantList & handle of p & ","
                        end repeat
                        if participantList is not "" then
                            set participantList to text 1 thru -2 of participantList
                        end if
                        
                        -- Get message count (approximate)
                        set msgCount to count of messages of c
                        
                        set output to output & chatName & "|||" & chatId & "|||" & participantList & "|||" & msgCount & "###CHAT###"
                        set chatCount to chatCount + 1
                    end try
                end repeat
            on error errMsg
                return "ERROR:" & errMsg
            end try
            
            return output
        end tell
        """

        out = _run_osascript(script)
        if not out or out.startswith("ERROR:"):
            return []

        conversations = []
        for chat_str in out.split("###CHAT###"):
            if not chat_str.strip():
                continue
            parts = chat_str.split("|||")
            if len(parts) >= 4:
                participants = [p.strip() for p in parts[2].split(",") if p.strip()]
                conversations.append(
                    {
                        "name": parts[0],
                        "id": parts[1],
                        "participants": participants,
                        "message_count": int(parts[3]) if parts[3].isdigit() else 0,
                    }
                )
        return conversations


class GetUnreadMessageCount(BaseNode):
    """
    Get the count of unread messages in Messages.app.
    messages, imessage, automation, macos, communication

    Use cases:
    - Check for new messages in workflows
    - Trigger actions based on unread count
    - Monitor message status
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> int:
        script = """
        tell application "Messages"
            set unreadCount to 0
            
            try
                repeat with c in chats
                    try
                        set unreadCount to unreadCount + (count of (messages of c whose read status is false))
                    end try
                end repeat
            on error
                return 0
            end try
            
            return unreadCount
        end tell
        """

        out = _run_osascript(script)
        return int(out) if out.isdigit() else 0


class SearchMessages(BaseNode):
    """
    Search through messages in Messages.app.
    messages, imessage, automation, macos, communication, search

    Use cases:
    - Find messages containing specific text
    - Search conversation history
    - Locate specific information in messages
    """

    query: str = Field(
        default="",
        description="Text to search for in messages",
    )
    participant: str = Field(
        default="",
        description="Optional: limit search to messages from/to this participant",
    )
    limit: int = Field(
        default=50,
        description="Maximum number of results to return",
        ge=1,
        le=200,
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["query", "participant"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> list[dict]:
        if not self.query.strip():
            raise ValueError("Search query is required")

        query = escape_for_applescript(self.query.lower())
        participant = (
            escape_for_applescript(self.participant) if self.participant.strip() else ""
        )

        # Build chat filter
        if participant:
            chat_filter = f'chats whose participants contains buddy "{participant}"'
        else:
            chat_filter = "chats"

        script = f"""
        tell application "Messages"
            set output to ""
            set resultCount to 0
            set maxResults to {self.limit}
            set searchQuery to "{query}"
            
            try
                repeat with c in {chat_filter}
                    if resultCount >= maxResults then exit repeat
                    
                    try
                        set chatName to name of c
                        
                        repeat with msg in messages of c
                            if resultCount >= maxResults then exit repeat
                            
                            try
                                set msgText to text of msg
                                if msgText contains searchQuery then
                                    set msgSender to handle of sender of msg
                                    set msgDate to date sent of msg as string
                                    set msgIsFromMe to "false"
                                    if sender of msg is me then set msgIsFromMe to "true"
                                    
                                    set output to output & chatName & "|||" & msgText & "|||" & msgSender & "|||" & msgDate & "|||" & msgIsFromMe & "###MSG###"
                                    set resultCount to resultCount + 1
                                end if
                            end try
                        end repeat
                    end try
                end repeat
            on error errMsg
                return "ERROR:" & errMsg
            end try
            
            return output
        end tell
        """

        out = _run_osascript(script)
        if not out or out.startswith("ERROR:"):
            return []

        messages = []
        for msg_str in out.split("###MSG###"):
            if not msg_str.strip():
                continue
            parts = msg_str.split("|||")
            if len(parts) >= 5:
                messages.append(
                    {
                        "conversation": parts[0],
                        "text": parts[1],
                        "sender": parts[2],
                        "date": parts[3],
                        "is_from_me": parts[4] == "true",
                    }
                )
        return messages


class MarkAsRead(BaseNode):
    """
    Mark all messages from a participant as read.
    messages, imessage, automation, macos, communication

    Use cases:
    - Clear unread notifications from a contact
    - Mark automated messages as read
    - Reset conversation status
    """

    participant: str = Field(
        default="",
        description="Phone number, email, or contact name to mark as read",
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["participant"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        if not self.participant.strip():
            raise ValueError("Participant is required")

        participant = escape_for_applescript(self.participant)

        script = f"""
        tell application "Messages"
            try
                set targetChat to 1st chat whose participants contains buddy "{participant}"
                repeat with msg in messages of targetChat
                    set read status of msg to true
                end repeat
                return "success"
            on error errMsg
                return "ERROR:" & errMsg
            end try
        end tell
        """

        out = _run_osascript(script)
        return not out.startswith("ERROR:")


class MarkAsUnread(BaseNode):
    """
    Mark messages from a participant as unread.
    messages, imessage, automation, macos, communication

    Use cases:
    - Flag messages for later review
    - Highlight important conversations
    - Create reminder notifications
    """

    participant: str = Field(
        default="",
        description="Phone number, email, or contact name to mark as unread",
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["participant"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        if not self.participant.strip():
            raise ValueError("Participant is required")

        participant = escape_for_applescript(self.participant)

        script = f"""
        tell application "Messages"
            try
                set targetChat to 1st chat whose participants contains buddy "{participant}"
                repeat with msg in messages of targetChat
                    set read status of msg to false
                end repeat
                return "success"
            on error errMsg
                return "ERROR:" & errMsg
            end try
        end tell
        """

        out = _run_osascript(script)
        return not out.startswith("ERROR:")


class GetConversationDetails(BaseNode):
    """
    Get detailed information about a specific conversation.
    messages, imessage, automation, macos, communication

    Use cases:
    - Get conversation metadata
    - Check conversation properties
    - Analyze chat characteristics
    """

    participant: str = Field(
        default="",
        description="Phone number, email, or contact name to get details for",
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["participant"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> dict:
        if not self.participant.strip():
            raise ValueError("Participant is required")

        participant = escape_for_applescript(self.participant)

        script = f"""
        tell application "Messages"
            try
                set targetChat to 1st chat whose participants contains buddy "{participant}"
                
                set chatName to name of targetChat
                set chatId to id of targetChat
                
                set participantList to ""
                repeat with p in participants of targetChat
                    set participantList to participantList & handle of p & ","
                end repeat
                if participantList is not "" then
                    set participantList to text 1 thru -2 of participantList
                end if
                
                set totalMessages to count of messages of targetChat
                set unreadCount to count of (messages of targetChat whose read status is false)
                
                return chatName & "|||" & chatId & "|||" & participantList & "|||" & totalMessages & "|||" & unreadCount
            on error errMsg
                return "ERROR:" & errMsg
            end try
        end tell
        """

        out = _run_osascript(script)
        if out.startswith("ERROR:"):
            return {}

        parts = out.split("|||")
        if len(parts) >= 5:
            participants = [p.strip() for p in parts[2].split(",") if p.strip()]
            return {
                "name": parts[0],
                "id": parts[1],
                "participants": participants,
                "total_messages": int(parts[3]) if parts[3].isdigit() else 0,
                "unread_count": int(parts[4]) if parts[4].isdigit() else 0,
            }
        return {}


class SendAttachment(BaseNode):
    """
    Send a file attachment via iMessage.
    messages, imessage, automation, macos, communication

    Use cases:
    - Send images or documents
    - Share files in workflows
    - Attach files to messages
    """

    recipient: str = Field(
        default="",
        description="Phone number, email, or contact name to send attachment to",
    )
    file_path: str = Field(
        default="",
        description="Absolute path to the file to send",
    )
    message: str = Field(
        default="",
        description="Optional message text to include with attachment",
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["recipient", "file_path", "message"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> bool:
        if not self.recipient.strip():
            raise ValueError("Recipient is required")
        if not self.file_path.strip():
            raise ValueError("File path is required")

        file_path_obj = Path(self.file_path)
        if not file_path_obj.exists():
            raise ValueError(f"File not found: {self.file_path}")

        recipient = escape_for_applescript(self.recipient)
        file_path = escape_for_applescript(self.file_path)

        if self.message.strip():
            message_content = escape_for_applescript(self.message)
            script = f"""
            tell application "Messages"
                set targetService to 1st service whose service type = iMessage
                set targetBuddy to buddy "{recipient}" of targetService
                set theFile to POSIX file "{file_path}"
                set theAttachment to theFile as alias
                send "{message_content}" to targetBuddy
                send theAttachment to targetBuddy
            end tell
            """
        else:
            script = f"""
            tell application "Messages"
                set targetService to 1st service whose service type = iMessage
                set targetBuddy to buddy "{recipient}" of targetService
                set theFile to POSIX file "{file_path}"
                set theAttachment to theFile as alias
                send theAttachment to targetBuddy
            end tell
            """

        _run_osascript(script)
        return True


class GetLatestMessage(BaseNode):
    """
    Get the most recent message from a conversation.
    messages, imessage, automation, macos, communication

    Use cases:
    - Check for new messages
    - Get latest conversation update
    - Monitor message activity
    """

    participant: str = Field(
        default="",
        description="Phone number, email, or contact name to get latest message from",
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["participant"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> dict:
        if not self.participant.strip():
            raise ValueError("Participant is required")

        participant = escape_for_applescript(self.participant)

        script = f"""
        tell application "Messages"
            try
                set targetChat to 1st chat whose participants contains buddy "{participant}"
                set allMessages to messages of targetChat
                
                if (count of allMessages) > 0 then
                    set msg to last item of allMessages
                    set msgText to text of msg
                    set msgSender to handle of sender of msg
                    set msgDate to date sent of msg as string
                    set msgIsFromMe to "false"
                    if sender of msg is me then set msgIsFromMe to "true"
                    
                    return msgText & "|||" & msgSender & "|||" & msgDate & "|||" & msgIsFromMe
                else
                    return "NO_MESSAGES"
                end if
            on error errMsg
                return "ERROR:" & errMsg
            end try
        end tell
        """

        out = _run_osascript(script)
        if out.startswith("ERROR:") or out == "NO_MESSAGES":
            return {}

        parts = out.split("|||")
        if len(parts) >= 4:
            return {
                "text": parts[0],
                "sender": parts[1],
                "date": parts[2],
                "is_from_me": parts[3] == "true",
            }
        return {}
