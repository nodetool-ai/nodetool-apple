"""Tests for new Apple nodes utility functions."""

import pytest


def test_finder_tag_enum_values():
    """Test that FinderTag enum has expected values."""
    from nodetool.nodes.apple.finder import FinderTag

    assert FinderTag.NONE.value == "0"
    assert FinderTag.RED.value == "6"
    assert FinderTag.GREEN.value == "2"


def test_player_state_enum_values():
    """Test that PlayerState enum has expected values."""
    from nodetool.nodes.apple.music import PlayerState

    assert PlayerState.PLAY.value == "play"
    assert PlayerState.PAUSE.value == "pause"
    assert PlayerState.NEXT.value == "next"


def test_text_case_enum_values():
    """Test that TextCase enum has expected values."""
    from nodetool.nodes.apple.text_services import ConvertTextCase

    assert ConvertTextCase.TextCase.UPPER.value == "upper"
    assert ConvertTextCase.TextCase.LOWER.value == "lower"
    assert ConvertTextCase.TextCase.TITLE.value == "title"


def test_word_count_basic():
    """Test WordCount node basic functionality."""
    from nodetool.nodes.apple.text_services import WordCount
    import asyncio

    node = WordCount(text="Hello world. This is a test.")

    # Create a mock context - we only need text parsing
    class MockContext:
        pass

    result = asyncio.get_event_loop().run_until_complete(node.process(MockContext()))
    assert result["words"] == 6
    assert result["characters"] > 0


def test_extract_urls():
    """Test ExtractURLs node."""
    from nodetool.nodes.apple.text_services import ExtractURLs
    import asyncio

    text = "Check out https://example.com and also http://test.org/page for more info."
    node = ExtractURLs(text=text)

    class MockContext:
        pass

    result = asyncio.get_event_loop().run_until_complete(node.process(MockContext()))
    assert "https://example.com" in result
    assert "http://test.org/page" in result


def test_extract_emails():
    """Test ExtractEmails node."""
    from nodetool.nodes.apple.text_services import ExtractEmails
    import asyncio

    text = "Contact us at support@example.com or sales@test.org."
    node = ExtractEmails(text=text)

    class MockContext:
        pass

    result = asyncio.get_event_loop().run_until_complete(node.process(MockContext()))
    assert "support@example.com" in result
    assert "sales@test.org" in result


def test_system_volume_range():
    """Test SetSystemVolume node volume validation."""
    from nodetool.nodes.apple.system import SetSystemVolume
    from pydantic import ValidationError

    # Valid volumes
    node = SetSystemVolume(volume=50)
    assert node.volume == 50

    node = SetSystemVolume(volume=0)
    assert node.volume == 0

    node = SetSystemVolume(volume=100)
    assert node.volume == 100

    # Invalid volumes should raise validation error
    with pytest.raises(ValidationError):
        SetSystemVolume(volume=-1)

    with pytest.raises(ValidationError):
        SetSystemVolume(volume=101)


def test_new_nodes_cacheable():
    """Test is_cacheable for new nodes."""
    from nodetool.nodes.apple.system import (
        GetSystemVolume,
        SetSystemVolume,
        GetDarkMode,
    )
    from nodetool.nodes.apple.finder import (
        GetDesktopPath,
        GetDownloadsPath,
        RevealInFinder,
    )
    from nodetool.nodes.apple.music import GetCurrentTrack, SearchMusic
    from nodetool.nodes.apple.text_services import (
        WordCount,
        ExtractURLs,
        DetectLanguage,
    )

    # System nodes that read/write state should not be cacheable
    assert GetSystemVolume.is_cacheable() is False
    assert SetSystemVolume.is_cacheable() is False
    assert GetDarkMode.is_cacheable() is False

    # Path nodes return static data, can be cacheable
    assert GetDesktopPath.is_cacheable() is True
    assert GetDownloadsPath.is_cacheable() is True

    # Action nodes should not be cacheable
    assert RevealInFinder.is_cacheable() is False
    assert GetCurrentTrack.is_cacheable() is False

    # Search with same query can be cached
    assert SearchMusic.is_cacheable() is True

    # Text processing with same input can be cached
    assert WordCount.is_cacheable() is True
    assert ExtractURLs.is_cacheable() is True
    assert DetectLanguage.is_cacheable() is True
