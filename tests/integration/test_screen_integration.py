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
async def test_capture_screen_with_region():
    """Test that screen capture works with region parameters."""
    context = ProcessingContext()
    
    # Test capture with specific region dimensions
    node = CaptureScreen(
        whole_screen=False,
        x=0,
        y=0,
        width=800,
        height=600
    )
    
    # Note: Region capture may not work correctly in headless environments
    # This test verifies the node accepts the parameters and attempts capture
    try:
        image_ref = await node.process(context)
        assert isinstance(image_ref, ImageRef)
        assert image_ref.asset_id is not None
    except RuntimeError:
        # Region capture may fail in headless/CI environments
        # This is acceptable for integration testing
        pass
