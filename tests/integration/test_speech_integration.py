"""
Integration tests for Apple Speech node on macOS.
These tests run on actual macOS GitHub Actions runners.
"""

import pytest
from nodetool.workflows.processing_context import ProcessingContext
from nodetool.nodes.apple.speech import SayText, MacOSVoice


@pytest.mark.asyncio
async def test_say_text_basic():
    """Test basic text-to-speech on macOS."""
    context = ProcessingContext()
    node = SayText(
        text="Hello from integration test",
        voice=MacOSVoice.SAMANTHA
    )
    
    # Process should complete without errors and return True or False
    result = await node.process(context)
    
    # The node returns a boolean indicating success
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_say_text_with_different_voice():
    """Test text-to-speech with a different voice."""
    context = ProcessingContext()
    node = SayText(
        text="Testing voice",
        voice=MacOSVoice.DANIEL  # UK English voice
    )
    
    result = await node.process(context)
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_say_text_empty_string():
    """Test text-to-speech with empty string."""
    context = ProcessingContext()
    node = SayText(
        text="",
        voice=MacOSVoice.SAMANTHA
    )
    
    # Should handle empty text gracefully
    result = await node.process(context)
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_say_text_not_cacheable():
    """Test that SayText is not cacheable."""
    # Speech actions should not be cached as they have side effects
    assert SayText.is_cacheable() is False
