"""
Integration tests for Apple Dictionary node on macOS.
These tests run on actual macOS GitHub Actions runners.
"""

import pytest
from nodetool.workflows.processing_context import ProcessingContext
from nodetool.nodes.apple.dictionary import SearchDictionary


@pytest.mark.asyncio
async def test_search_dictionary_basic():
    """Test basic dictionary search on macOS."""
    context = ProcessingContext()
    node = SearchDictionary(term="apple", max_results=3)
    
    definitions = await node.process(context)
    
    # Should return a list of definitions
    assert isinstance(definitions, list)
    assert len(definitions) > 0
    
    # Each definition should be a non-empty string
    for definition in definitions:
        assert isinstance(definition, str)
        assert len(definition) > 0


@pytest.mark.asyncio
async def test_search_dictionary_empty_term():
    """Test dictionary search with empty term."""
    context = ProcessingContext()
    node = SearchDictionary(term="", max_results=1)
    
    definitions = await node.process(context)
    
    # Should return empty list for empty term
    assert isinstance(definitions, list)
    assert len(definitions) == 0


@pytest.mark.asyncio
async def test_search_dictionary_max_results():
    """Test that max_results is respected."""
    context = ProcessingContext()
    node = SearchDictionary(term="test", max_results=2)
    
    definitions = await node.process(context)
    
    # Should not exceed max_results
    assert isinstance(definitions, list)
    assert len(definitions) <= 2


@pytest.mark.asyncio
async def test_dictionary_cacheable():
    """Test that SearchDictionary is cacheable."""
    assert SearchDictionary.is_cacheable() is True
