"""
Integration tests for Apple Spotlight nodes on macOS.
These tests run on actual macOS GitHub Actions runners.
"""

import pytest
from nodetool.workflows.processing_context import ProcessingContext
from nodetool.nodes.apple.spotlight import SpotlightSearch


@pytest.mark.asyncio
async def test_spotlight_search_basic():
    """Test basic Spotlight search on macOS."""
    context = ProcessingContext()
    
    # Search for common files that should exist on most macOS systems
    node = SpotlightSearch(query="kMDItemKind == 'Folder'", limit=5)
    
    results = await node.process(context)
    
    # Should return a list of paths
    assert isinstance(results, list)
    
    # Each result should be a non-empty string path
    for path in results:
        assert isinstance(path, str)
        assert len(path) > 0


@pytest.mark.asyncio
async def test_spotlight_search_empty_query():
    """Test Spotlight search with empty query."""
    context = ProcessingContext()
    
    node = SpotlightSearch(query="", limit=10)
    results = await node.process(context)
    
    # Empty query should return empty results
    assert isinstance(results, list)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_spotlight_search_with_limit():
    """Test that limit parameter is respected."""
    context = ProcessingContext()
    
    node = SpotlightSearch(query="kMDItemContentType == 'public.item'", limit=3)
    results = await node.process(context)
    
    # Should not exceed the limit
    assert isinstance(results, list)
    assert len(results) <= 3


@pytest.mark.asyncio
async def test_spotlight_cacheable():
    """Test that SpotlightSearch is cacheable."""
    assert SpotlightSearch.is_cacheable() is True


@pytest.mark.asyncio
async def test_mdfind_available():
    """Test that mdfind CLI is available on macOS."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["mdfind", "-h"],
            check=False,
            capture_output=True,
            text=True,
        )
        # mdfind should be available on macOS
        assert result.returncode in [0, 1]  # 0 for help, 1 for usage error
    except FileNotFoundError:
        pytest.fail("mdfind CLI not found - this test requires macOS")
