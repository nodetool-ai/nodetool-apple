"""Tests for Apple screen capture nodes."""

import asyncio
import platform
import pytest

from nodetool.nodes.apple.window_management import (
    GetScreenResolution,
    GetWindowList,
    CaptureWindow,
    GetActiveWindow,
    ListApplications,
    FocusApplication,
)


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS-only tests")
class TestScreenNodes:
    """Test screen capture and window management nodes."""

    async def test_get_screen_resolution(self):
        """Test GetScreenResolution node."""
        node = GetScreenResolution()
        
        class MockContext:
            pass
        
        result = await node.process(MockContext())
        
        assert isinstance(result, dict)
        assert "width" in result
        assert "height" in result
        assert "display_id" in result
        assert "bounds" in result
        assert "scale_factor" in result
        
        # Check that width and height are reasonable
        assert result["width"] > 0
        assert result["height"] > 0
        assert isinstance(result["width"], int)
        assert isinstance(result["height"], int)
        
        # Check bounds structure
        bounds = result["bounds"]
        assert "x" in bounds
        assert "y" in bounds
        assert "width" in bounds
        assert "height" in bounds
        assert bounds["width"] == result["width"]
        assert bounds["height"] == result["height"]

    async def test_get_window_list(self):
        """Test GetWindowList node."""
        node = GetWindowList()
        
        class MockContext:
            pass
        
        result = await node.process(MockContext())
        
        assert isinstance(result, list)
        
        if result:  # If there are windows
            window = result[0]
            assert isinstance(window, dict)
            assert "name" in window
            assert "owner" in window
            assert "layer" in window
            assert "bounds" in window
            assert "window_id" in window

    async def test_list_applications(self):
        """Test ListApplications node."""
        node = ListApplications()
        
        class MockContext:
            pass
        
        result = await node.process(MockContext())
        
        assert isinstance(result, list)
        
        if result:  # If there are applications
            app = result[0]
            assert isinstance(app, dict)
            assert "name" in app
            assert "bundle_id" in app
            assert "process_id" in app
            assert "is_hidden" in app
            assert "is_terminated" in app

    async def test_get_active_window(self):
        """Test GetActiveWindow node."""
        node = GetActiveWindow()
        
        class MockContext:
            pass
        
        result = await node.process(MockContext())
        
        assert isinstance(result, dict)
        
        if "error" not in result:
            assert "application" in result
            assert "bundle_id" in result
            assert "window" in result
            
            window = result["window"]
            assert isinstance(window, dict)
            assert "name" in window
            assert "bounds" in window
            assert "window_id" in window

    def test_nodes_cacheable(self):
        """Test is_cacheable for screen nodes."""
        # System information nodes can be cached
        assert GetScreenResolution.is_cacheable() is True
        
        # Window/application listing nodes can be cached
        assert GetWindowList.is_cacheable() is True
        assert ListApplications.is_cacheable() is True
        
        # Active window detection changes frequently, should not be cached
        assert GetActiveWindow.is_cacheable() is False
        
        # Action nodes should not be cached
        assert CaptureWindow.is_cacheable() is False
        assert FocusApplication.is_cacheable() is False

    def test_capture_window_validation(self):
        """Test CaptureWindow node parameter validation."""
        from pydantic import ValidationError
        
        # Valid initialization
        node = CaptureWindow(window_name="Test Window")
        assert node.window_name == "Test Window"
        assert node.window_id == 0
        assert node.owner_name == ""
        
        # Valid initialization with ID
        node = CaptureWindow(window_id=12345)
        assert node.window_id == 12345
        assert node.window_name == ""

    def test_focus_application_validation(self):
        """Test FocusApplication node parameter validation."""
        from pydantic import ValidationError
        
        # Valid initialization
        node = FocusApplication(application_name="Safari")
        assert node.application_name == "Safari"
        assert node.bundle_id == ""
        
        # Valid initialization with bundle ID
        node = FocusApplication(application_name="Safari", bundle_id="com.apple.Safari")
        assert node.application_name == "Safari"
        assert node.bundle_id == "com.apple.Safari"


if __name__ == "__main__":
    # Run basic tests
    async def run_basic_tests():
        test_instance = TestScreenNodes()
        
        print("Testing GetScreenResolution...")
        await test_instance.test_get_screen_resolution()
        print("✓ GetScreenResolution works")
        
        print("Testing GetWindowList...")
        await test_instance.test_get_window_list()
        print("✓ GetWindowList works")
        
        print("Testing ListApplications...")
        await test_instance.test_list_applications()
        print("✓ ListApplications works")
        
        print("Testing GetActiveWindow...")
        await test_instance.test_get_active_window()
        print("✓ GetActiveWindow works")
        
        print("Testing cacheable properties...")
        test_instance.test_nodes_cacheable()
        print("✓ Cacheable properties correct")
        
        print("Testing parameter validation...")
        test_instance.test_capture_window_validation()
        test_instance.test_focus_application_validation()
        print("✓ Parameter validation works")
        
        print("\nAll tests passed! 🎉")

    if platform.system() == "Darwin":
        asyncio.run(run_basic_tests())
    else:
        print("Skipping tests - not on macOS")