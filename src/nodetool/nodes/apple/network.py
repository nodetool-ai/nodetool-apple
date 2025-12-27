"""
Network and WiFi related nodes for macOS.
"""

from __future__ import annotations

import subprocess
from typing import Any

from pydantic import Field

from nodetool.workflows.base_node import BaseNode
from nodetool.workflows.processing_context import ProcessingContext


class GetWiFiStatus(BaseNode):
    """
    Get the current WiFi connection status and network info.
    network, wifi, macos, automation

    Use cases:
    - Check connectivity before network-dependent workflows
    - Monitor network changes
    - Log network info for troubleshooting
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> dict:
        info: dict[str, Any] = {
            "is_connected": False,
            "ssid": "",
            "bssid": "",
            "channel": 0,
            "rssi": 0,
            "noise": 0,
        }

        try:
            # Get WiFi interface name (usually en0)
            result = subprocess.run(
                [
                    "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport",
                    "-I",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return info

            output = result.stdout
            for line in output.strip().split("\n"):
                line = line.strip()
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                if key == "SSID":
                    info["ssid"] = value
                    info["is_connected"] = bool(value)
                elif key == "BSSID":
                    info["bssid"] = value
                elif key == "channel":
                    try:
                        info["channel"] = int(value.split(",")[0])
                    except ValueError:
                        pass
                elif key == "agrCtlRSSI":
                    try:
                        info["rssi"] = int(value)
                    except ValueError:
                        pass
                elif key == "agrCtlNoise":
                    try:
                        info["noise"] = int(value)
                    except ValueError:
                        pass

        except FileNotFoundError:
            pass

        return info


class GetPublicIP(BaseNode):
    """
    Get the public IP address of this machine.
    network, ip, macos, automation

    Use cases:
    - Log external IP for remote access setup
    - Monitor IP changes
    - Network diagnostics
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> str:
        try:
            # Use dig to query external DNS for our IP
            result = subprocess.run(
                ["dig", "+short", "myip.opendns.com", "@resolver1.opendns.com"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Fallback to curl
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "5", "https://api.ipify.org"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return ""


class GetLocalIP(BaseNode):
    """
    Get the local (LAN) IP address of this machine.
    network, ip, macos, automation

    Use cases:
    - Find local IP for network services
    - Set up local device communication
    - Network configuration workflows
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> str:
        try:
            # Get the IP of the default route interface
            result = subprocess.run(
                ["ipconfig", "getifaddr", "en0"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()

            # Try en1 (sometimes wireless is here)
            result = subprocess.run(
                ["ipconfig", "getifaddr", "en1"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()

        except FileNotFoundError:
            pass

        return ""


class GetHostname(BaseNode):
    """
    Get the hostname of this machine.
    network, hostname, macos, automation

    Use cases:
    - Identify machine in workflows
    - Multi-machine coordination
    - Network service setup
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return True

    async def process(self, context: ProcessingContext) -> str:
        import socket

        return socket.gethostname()


class PingHost(BaseNode):
    """
    Ping a host to check network connectivity.
    network, ping, macos, automation

    Use cases:
    - Check if a server is reachable
    - Network health monitoring
    - Conditional workflows based on connectivity
    """

    host: str = Field(default="", description="Hostname or IP address to ping")
    count: int = Field(default=1, ge=1, le=10, description="Number of ping packets")
    timeout: int = Field(default=5, ge=1, le=30, description="Timeout in seconds")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["host", "count"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    async def process(self, context: ProcessingContext) -> dict:
        if not self.host.strip():
            raise ValueError("host is required")

        try:
            result = subprocess.run(
                ["ping", "-c", str(self.count), "-t", str(self.timeout), self.host],
                capture_output=True,
                text=True,
                timeout=self.timeout + 5,
            )

            output = result.stdout
            is_reachable = result.returncode == 0

            # Parse average ping time
            avg_time = 0.0
            for line in output.split("\n"):
                if "avg" in line.lower():
                    # Format: round-trip min/avg/max/stddev = 1.234/5.678/9.012/1.234 ms
                    parts = line.split("=")
                    if len(parts) > 1:
                        times = parts[1].strip().split("/")
                        if len(times) > 1:
                            try:
                                avg_time = float(times[1])
                            except ValueError:
                                pass

            return {
                "is_reachable": is_reachable,
                "avg_ms": avg_time,
                "output": output,
            }

        except subprocess.TimeoutExpired:
            return {
                "is_reachable": False,
                "avg_ms": 0.0,
                "output": "Timeout",
            }
        except FileNotFoundError as e:
            raise RuntimeError("ping command not found") from e
