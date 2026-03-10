"""
Integration tests for Apple Shortcuts nodes on macOS.
These tests run on actual macOS GitHub Actions runners.
"""

import pytest
from nodetool.workflows.processing_context import ProcessingContext
from nodetool.nodes.apple.shortcuts import ListShortcuts, RunShortcut


@pytest.mark.asyncio
async def test_list_shortcuts():
    """Test listing shortcuts on macOS."""
    context = ProcessingContext()
    node = ListShortcuts()
    
    shortcuts = await node.process(context)
    
    # Should return a list (could be empty if no shortcuts are installed)
    assert isinstance(shortcuts, list)
    
    # Each item should be a string
    for shortcut in shortcuts:
        assert isinstance(shortcut, str)
        assert len(shortcut) > 0


@pytest.mark.asyncio
async def test_shortcuts_cli_available():
    """Test that the shortcuts CLI is available on macOS."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["shortcuts", "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
    except FileNotFoundError:
        pytest.fail("shortcuts CLI not found - this test requires macOS 12+")
