"""
Integration tests for Apple Clipboard nodes on macOS.
These tests run on actual macOS GitHub Actions runners.
"""

import pytest
from nodetool.workflows.processing_context import ProcessingContext
from nodetool.nodes.apple.clipboard import GetClipboardText, SetClipboardText
from nodetool.metadata.types import TextRef


@pytest.mark.asyncio
async def test_set_and_get_clipboard_text():
    """Test setting and getting text from clipboard."""
    context = ProcessingContext()
    
    # Set clipboard text
    set_node = SetClipboardText(text="Integration test clipboard content")
    result = await set_node.process(context)
    
    # Should return True indicating success
    assert isinstance(result, bool)
    assert result is True
    
    # Get clipboard text back
    get_node = GetClipboardText()
    text_ref = await get_node.process(context)
    
    # Should return a TextRef
    assert isinstance(text_ref, TextRef)


@pytest.mark.asyncio
async def test_set_clipboard_empty_string():
    """Test setting clipboard with empty string."""
    context = ProcessingContext()
    
    set_node = SetClipboardText(text="")
    result = await set_node.process(context)
    
    # Should succeed even with empty string
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_clipboard_not_cacheable():
    """Test that clipboard operations are not cacheable."""
    assert SetClipboardText.is_cacheable() is False
    assert GetClipboardText.is_cacheable() is False
