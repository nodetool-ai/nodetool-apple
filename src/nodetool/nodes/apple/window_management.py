from cmath import rect

import Foundation  # type: ignore
import Quartz  # type: ignore
from nodetool.metadata.types import ImageRef
from nodetool.workflows.base_node import BaseNode
from nodetool.workflows.processing_context import ProcessingContext
from pydantic import Field


class CaptureScreen(BaseNode):
    """
    Capture screen content via PyObjC
    screen, automation, macos, media
    """

    whole_screen: bool = Field(default=True, description="Capture the whole screen")
    x: int = Field(default=0, description="X coordinate of the region to capture")
    y: int = Field(default=0, description="Y coordinate of the region to capture")
    width: int = Field(default=1920, description="Width of the region to capture")
    height: int = Field(default=1080, description="Height of the region to capture")

    async def process(self, context: ProcessingContext) -> ImageRef:
        main_display = Quartz.CGMainDisplayID()  # type: ignore

        # If region is specified, capture that region, otherwise capture full screen
        if self.whole_screen:
            image = Quartz.CGDisplayCreateImage(main_display)  # type: ignore
        else:
            # Capture specific region
            cg_rect = Quartz.CGRectMake(
                self.x, self.y, self.width, self.height
            )  # type: ignore
            image = Quartz.CGWindowListCreateImage(  # type: ignore
                cg_rect,
                Quartz.kCGWindowListOptionOnScreenOnly,  # type: ignore
                Quartz.kCGNullWindowID,  # type: ignore
                Quartz.kCGWindowImageDefault,  # type: ignore
            )  # type: ignore

        if image is None:
            raise RuntimeError("Failed to capture screen")

        data = Quartz.CFDataCreateMutable(None, 0)  # type: ignore
        dest = Quartz.CGImageDestinationCreateWithData(data, "public.png", 1, None)  # type: ignore

        if dest is None:
            raise RuntimeError("Failed to create image destination")

        Quartz.CGImageDestinationAddImage(dest, image, None)  # type: ignore
        Quartz.CGImageDestinationFinalize(dest)  # type: ignore

        return await context.image_from_bytes(bytes(data))


class GetWindowList(BaseNode):
    """
    Get list of all open windows
    window, automation, macos, system
    """

    @classmethod
    def is_cacheable(cls) -> bool:
        return True

    async def process(self, context: ProcessingContext) -> list[dict]:
        window_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID
        )
        
        windows = []
        for window_info in window_list:
            window_dict = dict(window_info)
            windows.append({
                "name": window_dict.get("kCGWindowName", ""),
                "owner": window_dict.get("kCGWindowOwnerName", ""),
                "layer": window_dict.get("kCGWindowLayer", 0),
                "bounds": window_dict.get("kCGWindowBounds", {}),
                "window_id": window_dict.get("kCGWindowNumber", 0)
            })
        
        return windows


class CaptureWindow(BaseNode):
    """
    Capture specific window by name or ID
    window, capture, automation, macos
    """

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    window_name: str = Field(default="", description="Name of the window to capture")
    window_id: int = Field(default=0, description="Window ID to capture (overrides name)")
    owner_name: str = Field(default="", description="Application name that owns the window")

    async def process(self, context: ProcessingContext) -> ImageRef:
        window_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID
        )
        
        target_window_id = None
        for window_info in window_list:
            window_dict = dict(window_info)
            
            if self.window_id > 0:
                if window_dict.get("kCGWindowNumber") == self.window_id:
                    target_window_id = self.window_id
                    break
            elif self.window_name:
                if (window_dict.get("kCGWindowName") == self.window_name and 
                    (not self.owner_name or window_dict.get("kCGWindowOwnerName") == self.owner_name)):
                    target_window_id = window_dict.get("kCGWindowNumber")
                    break
        
        if target_window_id is None:
            raise RuntimeError(f"Window not found: {self.window_name or self.window_id}")
        
        image = Quartz.CGWindowListCreateImage(
            Quartz.CGRectNull,
            Quartz.kCGWindowListOptionOnScreenOnly,
            target_window_id,
            Quartz.kCGWindowImageDefault
        )
        
        if image is None:
            raise RuntimeError("Failed to capture window")
        
        data = Quartz.CFDataCreateMutable(None, 0)
        dest = Quartz.CGImageDestinationCreateWithData(data, "public.png", 1, None)
        
        if dest is None:
            raise RuntimeError("Failed to create image destination")
        
        Quartz.CGImageDestinationAddImage(dest, image, None)
        Quartz.CGImageDestinationFinalize(dest)
        
        return await context.image_from_bytes(bytes(data))


class GetScreenResolution(BaseNode):
    """
    Get screen resolution and display information
    screen, display, system, macos
    """

    @classmethod
    def is_cacheable(cls) -> bool:
        return True

    async def process(self, context: ProcessingContext) -> dict:
        main_display = Quartz.CGMainDisplayID()
        
        # Get screen dimensions
        width = Quartz.CGDisplayPixelsWide(main_display)
        height = Quartz.CGDisplayPixelsHigh(main_display)
        
        # Get screen bounds
        bounds = Quartz.CGDisplayBounds(main_display)
        
        # Get display ID and other info
        display_info = {
            "width": width,
            "height": height,
            "bounds": {
                "x": bounds.origin.x,
                "y": bounds.origin.y,
                "width": bounds.size.width,
                "height": bounds.size.height
            },
            "display_id": main_display,
            "scale_factor": Quartz.CGDisplayGetScalingFactor(main_display) if hasattr(Quartz, 'CGDisplayGetScalingFactor') else 1.0
        }
        
        return display_info


class GetActiveWindow(BaseNode):
    """
    Get information about the currently active window
    window, active, automation, macos
    """

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> dict:
        # Get the frontmost application
        front_app = Foundation.NSWorkspace.sharedWorkspace().frontmostApplication()
        
        if front_app is None:
            return {"error": "No active application found"}
        
        # Get window list for the frontmost application
        window_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID
        )
        
        active_windows = []
        for window_info in window_list:
            window_dict = dict(window_info)
            if (window_dict.get("kCGWindowOwnerName") == front_app.localizedName() and
                window_dict.get("kCGWindowLayer") == 0):  # Normal window layer
                active_windows.append(window_dict)
        
        if not active_windows:
            return {
                "application": front_app.localizedName(),
                "bundle_id": front_app.bundleIdentifier(),
                "windows": []
            }
        
        # Return the main window (usually the first one)
        main_window = active_windows[0]
        
        return {
            "application": front_app.localizedName(),
            "bundle_id": front_app.bundleIdentifier(),
            "window": {
                "name": main_window.get("kCGWindowName", ""),
                "bounds": main_window.get("kCGWindowBounds", {}),
                "window_id": main_window.get("kCGWindowNumber", 0)
            }
        }


class ListApplications(BaseNode):
    """
    List all running applications
    applications, system, automation, macos
    """

    @classmethod
    def is_cacheable(cls) -> bool:
        return True

    async def process(self, context: ProcessingContext) -> list[dict]:
        workspace = Foundation.NSWorkspace.sharedWorkspace()
        running_apps = workspace.runningApplications()
        
        applications = []
        for app in running_apps:
            app_info = {
                "name": app.localizedName(),
                "bundle_id": app.bundleIdentifier(),
                "bundle_url": app.bundleURL().absoluteString() if app.bundleURL() else "",
                "executable_url": app.executableURL().absoluteString() if app.executableURL() else "",
                "is_hidden": app.isHidden(),
                "is_terminated": app.isTerminated(),
                "process_id": app.processIdentifier()
            }
            applications.append(app_info)
        
        return applications


class FocusApplication(BaseNode):
    """
    Bring an application to the foreground
    focus, application, automation, macos
    """

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    application_name: str = Field(description="Name of the application to focus")
    bundle_id: str = Field(default="", description="Bundle ID of the application (overrides name)")

    async def process(self, context: ProcessingContext) -> dict:
        workspace = Foundation.NSWorkspace.sharedWorkspace()
        running_apps = workspace.runningApplications()
        
        target_app = None
        for app in running_apps:
            if self.bundle_id:
                if app.bundleIdentifier() == self.bundle_id:
                    target_app = app
                    break
            else:
                if app.localizedName() == self.application_name:
                    target_app = app
                    break
        
        if target_app is None:
            raise RuntimeError(f"Application not found: {self.bundle_id or self.application_name}")
        
        # Activate the application
        success = target_app.activateWithOptions_(Foundation.NSApplicationActivateIgnoringOtherApps)
        
        return {
            "application": target_app.localizedName(),
            "bundle_id": target_app.bundleIdentifier(),
            "activated": success
        }
