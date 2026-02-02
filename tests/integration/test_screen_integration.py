"""
Integration tests for Apple Screen capture node on macOS.
These tests run on actual macOS GitHub Actions runners.
"""

import pytest
from nodetool.workflows.processing_context import ProcessingContext
from nodetool.nodes.apple.screen import CaptureScreen
from nodetool.metadata.types import ImageRef


@pytest.mark.asyncio
async def test_capture_whole_screen():
    """Test capturing the whole screen on macOS."""
    context = ProcessingContext()
    node = CaptureScreen(whole_screen=True)
    
    image_ref = await node.process(context)
    
    # Should return an ImageRef
    assert isinstance(image_ref, ImageRef)
    assert image_ref.asset_id is not None


@pytest.mark.asyncio
async def test_capture_screen_with_dimensions():
    """Test that screen capture accepts dimension parameters."""
    context = ProcessingContext()
    
    # Test that node can be instantiated with dimension parameters
    node = CaptureScreen(
        whole_screen=False,
        x=0,
        y=0,
        width=800,
        height=600
    )
    
    # Verify parameters are set correctly
    assert node.whole_screen is False
    assert node.x == 0
    assert node.y == 0
    assert node.width == 800
    assert node.height == 600


@pytest.mark.asyncio
async def test_screen_capture_produces_valid_image():
    """Test that screen capture produces a valid image."""
    context = ProcessingContext()
    node = CaptureScreen(whole_screen=True)
    
    image_ref = await node.process(context)
    
    # Verify we got an image reference
    assert isinstance(image_ref, ImageRef)
    assert hasattr(image_ref, 'asset_id')
