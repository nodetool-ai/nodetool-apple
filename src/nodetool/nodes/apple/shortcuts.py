import subprocess
import tempfile
from enum import Enum
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field

from nodetool.metadata.types import AssetRef, DocumentRef, TextRef
from nodetool.runtime.resources import require_scope
from nodetool.workflows.base_node import BaseNode
from nodetool.workflows.processing_context import ProcessingContext


class ListShortcuts(BaseNode):
    """
    List Shortcuts available on the current macOS user account via the `shortcuts` CLI.
    shortcuts, macos, automation, productivity

    Use cases:
    - Populate a UI dropdown of available shortcuts
    - Verify a shortcut exists before running it
    - Discover “building block” shortcuts for an agent
    """

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return []

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    @staticmethod
    def _parse_shortcuts_list(output: str) -> list[str]:
        return [line.strip() for line in output.splitlines() if line.strip()]

    async def process(self, context: ProcessingContext) -> list[str]:
        try:
            result = subprocess.run(
                ["shortcuts", "list"],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as e:
            raise RuntimeError(
                "The `shortcuts` CLI was not found. This node requires macOS 12+."
            ) from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to list shortcuts: {e.stderr}") from e

        return self._parse_shortcuts_list(result.stdout)


class RunShortcut(BaseNode):
    """
    Run an Apple Shortcut via the `shortcuts` CLI, with optional file/text input and captured output.
    shortcuts, macos, automation, productivity

    Use cases:
    - Trigger complex app automations built in Shortcuts (Mail, Finder, Home, etc.)
    - Provide a human-approval “gate” inside Shortcuts before side effects
    - Bridge AI workflows to native macOS actions without bespoke API code
    """

    shortcut: str = Field(
        default="",
        description="Shortcut name or identifier to run",
    )
    inputs: list[AssetRef] = Field(
        default_factory=list,
        description="Optional files to pass into the shortcut as input",
    )
    input_text: str = Field(
        default="",
        description="Optional text input; passed as a temporary .txt file",
    )
    output_type: str = Field(
        default="public.plain-text",
        description="Shortcut output type as a UTI (e.g. public.plain-text, public.json)",
    )

    class OutputMode(str, Enum):
        TEXT = "text"
        DOCUMENT = "document"

    output_mode: OutputMode = Field(
        default=OutputMode.TEXT,
        description="Return output as text or as a stored document asset",
    )
    output_name: str = Field(
        default="shortcut-output.txt",
        description="Asset name when output_mode=document",
    )
    output_content_type: str = Field(
        default="text/plain",
        description="Asset content type when output_mode=document",
    )
    timeout_seconds: int = Field(
        default=120,
        ge=1,
        description="Max time to allow the shortcut to run",
    )

    class DecodeErrors(str, Enum):
        STRICT = "strict"
        REPLACE = "replace"
        IGNORE = "ignore"

    decode_errors: DecodeErrors = Field(
        default=DecodeErrors.REPLACE,
        description="How to handle output bytes decoding when output_mode=text",
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["shortcut", "input_text", "output_type", "output_mode"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return False

    @staticmethod
    def _file_path_from_asset_uri(uri: str) -> str | None:
        if not uri:
            return None
        parsed = urlparse(uri)
        if parsed.scheme != "file":
            return None
        return parsed.path

    @staticmethod
    def _build_command(
        shortcut: str,
        input_paths: list[str],
        output_path: str,
        output_type: str,
    ) -> list[str]:
        cmd = ["shortcuts", "run", shortcut, "--output-path", output_path]
        if output_type:
            cmd.extend(["--output-type", output_type])
        for input_path in input_paths:
            cmd.extend(["--input-path", input_path])
        return cmd

    async def _materialize_inputs(
        self, context: ProcessingContext, temp_dir: Path
    ) -> list[str]:
        input_paths: list[str] = []

        if self.input_text:
            text_path = temp_dir / "input.txt"
            text_path.write_text(self.input_text, encoding="utf-8")
            input_paths.append(str(text_path))

        for asset in self.inputs:
            file_uri_path = self._file_path_from_asset_uri(getattr(asset, "uri", ""))
            if file_uri_path and Path(file_uri_path).exists():
                input_paths.append(file_uri_path)
                continue

            data = await context.asset_to_bytes(asset)
            suffix = Path(file_uri_path).suffix if file_uri_path else ""
            if not suffix:
                suffix = ".dat"
            out_path = temp_dir / f"input-{len(input_paths)}{suffix}"
            out_path.write_bytes(data)
            input_paths.append(str(out_path))

        return input_paths

    async def process(self, context: ProcessingContext) -> TextRef | DocumentRef:
        if not self.shortcut.strip():
            raise ValueError("shortcut is required")

        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            output_path = temp_dir / "output"
            input_paths = await self._materialize_inputs(context, temp_dir)

            cmd = self._build_command(
                shortcut=self.shortcut,
                input_paths=input_paths,
                output_path=str(output_path),
                output_type=self.output_type,
            )

            try:
                result = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=False,
                    timeout=self.timeout_seconds,
                )
            except FileNotFoundError as e:
                raise RuntimeError(
                    "The `shortcuts` CLI was not found. This node requires macOS 12+."
                ) from e
            except subprocess.TimeoutExpired as e:
                raise RuntimeError(
                    f"Shortcut timed out after {self.timeout_seconds}s"
                ) from e
            except subprocess.CalledProcessError as e:
                stderr = (e.stderr or b"").decode("utf-8", errors="replace")
                raise RuntimeError(f"Failed to run shortcut: {stderr}") from e

            output_bytes = output_path.read_bytes() if output_path.exists() else b""
            if not output_bytes and getattr(result, "stdout", None):
                output_bytes = result.stdout

            if self.output_mode == self.OutputMode.DOCUMENT:
                asset = await context.create_asset(
                    self.output_name,
                    self.output_content_type,
                    BytesIO(output_bytes),
                )
                storage = require_scope().get_asset_storage()
                url = await storage.get_url(asset.file_name)
                return DocumentRef(asset_id=asset.id, uri=url)

            text = output_bytes.decode("utf-8", errors=self.decode_errors.value)
            return await context.text_from_str(text)
