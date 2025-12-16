import subprocess
from pathlib import Path
from typing import Any

from pydantic import Field

from nodetool.metadata.types import AssetRef
from nodetool.workflows.base_node import BaseNode
from nodetool.workflows.processing_context import ProcessingContext


class SpotlightSearch(BaseNode):
    """
    Search local files using macOS Spotlight (`mdfind`).
    spotlight, search, macos, retrieval

    Use cases:
    - Local RAG: find relevant docs before summarization/QA
    - Locate recently modified files by content/metadata
    - Retrieve assets by tags, kind, or filename patterns
    """

    query: str = Field(default="", description="Spotlight query (mdfind syntax)")
    limit: int = Field(default=20, ge=0, description="Maximum results to return")
    only_in: str = Field(
        default="",
        description="Optional directory to constrain search to (passed to mdfind -onlyin)",
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["query", "limit", "only_in"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return True

    @staticmethod
    def _run_mdfind(query: str, only_in: str | None) -> list[str]:
        cmd = ["mdfind", "-0"]
        if only_in:
            cmd.extend(["-onlyin", only_in])
        cmd.append(query)

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=False)
        except FileNotFoundError as e:
            raise RuntimeError("`mdfind` not found (this node requires macOS).") from e
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or b"").decode("utf-8", errors="replace")
            raise RuntimeError(f"Spotlight search failed: {stderr}") from e

        out = result.stdout or b""
        paths = [p.decode("utf-8", errors="replace") for p in out.split(b"\x00") if p]
        return [p for p in paths if p.strip()]

    async def process(self, context: ProcessingContext) -> list[str]:
        if not self.query.strip():
            return []

        only_in = self.only_in.strip() or None
        if only_in:
            only_in = str(Path(only_in).expanduser())

        paths = self._run_mdfind(self.query, only_in)
        if self.limit:
            paths = paths[: self.limit]

        return paths


class SpotlightMetadata(BaseNode):
    """
    Read Spotlight metadata for a file using `mdls`.
    spotlight, metadata, macos, retrieval

    Use cases:
    - Fetch title/authors/kind for retrieved files
    - Inspect tags, content type, and dates
    - Build structured context for agents
    """

    file: AssetRef = Field(description="File to inspect (usually from SpotlightSearch)")
    keys: list[str] = Field(
        default_factory=list,
        description="Optional mdls keys (e.g. ['kMDItemKind','kMDItemContentType']); empty means all",
    )

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["file", "keys"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return True

    @staticmethod
    def _parse_mdls(output: str) -> dict[str, Any]:
        res: dict[str, Any] = {}
        for line in output.splitlines():
            if " = " not in line:
                continue
            key, value = line.split(" = ", 1)
            key = key.strip()
            value = value.strip()
            res[key] = value
        return res

    async def process(self, context: ProcessingContext) -> dict[str, Any]:
        file_dict = await context.assets_to_workspace_files(self.file)
        if not isinstance(file_dict, dict) or "path" not in file_dict:
            raise RuntimeError("Failed to materialize file to workspace for mdls")

        path = str(file_dict["path"])
        cmd = ["mdls"]
        if self.keys:
            for key in self.keys:
                cmd.extend(["-name", key])
        cmd.append(path)

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        except FileNotFoundError as e:
            raise RuntimeError("`mdls` not found (this node requires macOS).") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Spotlight metadata failed: {e.stderr}") from e

        return self._parse_mdls(result.stdout)
