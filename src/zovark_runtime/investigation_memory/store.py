"""Local lossless investigation_memory storage substrate."""

from __future__ import annotations

import json
from pathlib import Path

from .errors import MemoryObjectNotFoundError, MemoryObjectTamperError, MemoryObjectValidationError
from .identity import build_memory_ref_id, sha256_hex, validate_memory_ref_id
from .metadata import MemoryObjectMetadata


class LocalInvestigationMemoryStore:
    """File-backed storage for exact memory object bytes and metadata.

    This class is a storage substrate only. It does not implement bounded
    retrieval, model-visible envelopes, proof package generation, or model
    context integration.
    """

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)

    def put_bytes(
        self,
        content: bytes,
        *,
        investigation_id: str,
        source_tool_call_ref: str,
        content_encoding: str = "bytes",
        source_capability_ref: str | None = None,
        source_input_hash: str | None = None,
        source_output_hash: str | None = None,
        execution_status: str | None = None,
        trace_ref: str | None = None,
        line_range_index_available: bool = False,
        record_range_index_available: bool = False,
    ) -> MemoryObjectMetadata:
        """Store exact bytes and deterministic metadata."""

        if not isinstance(content, bytes):
            raise MemoryObjectValidationError("content must be bytes")

        content_hash = sha256_hex(content)
        memory_ref_id = build_memory_ref_id(
            investigation_id=investigation_id,
            source_tool_call_ref=source_tool_call_ref,
            content_hash=content_hash,
        )
        metadata = MemoryObjectMetadata(
            memory_ref_id=memory_ref_id,
            investigation_id=investigation_id,
            source_tool_call_ref=source_tool_call_ref,
            content_hash=content_hash,
            content_size_bytes=len(content),
            content_encoding=content_encoding,
            source_capability_ref=source_capability_ref,
            source_input_hash=source_input_hash,
            source_output_hash=source_output_hash,
            execution_status=execution_status,
            trace_ref=trace_ref,
            line_range_index_available=line_range_index_available,
            record_range_index_available=record_range_index_available,
        )

        content_path = self._content_path(content_hash)
        metadata_path = self._metadata_path(memory_ref_id)
        # Refuse to write through a symlink at ANY path component (leaf or an
        # intermediate directory such as objects/<2hex>), including dangling ones.
        # Otherwise a pre-placed symlink could redirect the write — or the mkdir —
        # outside the store directory.
        self._assert_no_symlink_escape(content_path)
        self._assert_no_symlink_escape(metadata_path)
        content_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        if content_path.exists():
            existing = content_path.read_bytes()
            if sha256_hex(existing) != content_hash or len(existing) != len(content):
                raise MemoryObjectTamperError("existing content does not match content-addressed path")
        else:
            content_path.write_bytes(content)

        if metadata_path.exists():
            existing_metadata = self.load_metadata(memory_ref_id)
            if existing_metadata.to_dict() != metadata.to_dict():
                raise MemoryObjectValidationError("existing metadata differs for deterministic memory_ref_id")
        else:
            metadata_path.write_text(metadata.to_json() + "\n", encoding="utf-8")
        return metadata

    def load_metadata(self, memory_ref_id: str) -> MemoryObjectMetadata:
        """Load and validate metadata for a memory object."""

        validate_memory_ref_id(memory_ref_id)
        metadata_path = self._metadata_path(memory_ref_id)
        if not metadata_path.exists():
            raise MemoryObjectNotFoundError("memory object metadata not found")
        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise MemoryObjectTamperError("memory object metadata is not valid JSON") from exc
        if not isinstance(data, dict):
            raise MemoryObjectTamperError("memory object metadata must be a JSON object")
        metadata = MemoryObjectMetadata.from_dict(data)
        if metadata.memory_ref_id != memory_ref_id:
            raise MemoryObjectTamperError("memory object metadata does not match requested memory_ref_id")
        return metadata

    def read_bytes_for_verification(self, memory_ref_id: str) -> bytes:
        """Read exact bytes for storage verification only.

        This is not bounded retrieval and is not model-visible access.
        """

        metadata = self.load_metadata(memory_ref_id)
        content_path = self._content_path(metadata.content_hash)
        if not content_path.exists():
            raise MemoryObjectTamperError("memory object content is missing")
        return content_path.read_bytes()

    def verify(self, memory_ref_id: str) -> MemoryObjectMetadata:
        """Verify stored bytes against recorded hash and size."""

        metadata = self.load_metadata(memory_ref_id)
        content = self.read_bytes_for_verification(memory_ref_id)
        actual_hash = sha256_hex(content)
        if actual_hash != metadata.content_hash:
            raise MemoryObjectTamperError("memory object content hash mismatch")
        if len(content) != metadata.content_size_bytes:
            raise MemoryObjectTamperError("memory object content size mismatch")
        return metadata

    def _assert_no_symlink_escape(self, path: Path) -> None:
        """Refuse if any component of *path* under root_dir is a symlink.

        Checks every component (objects/<2hex>/<hash>.bin and the metadata
        equivalent), so neither the leaf nor an intermediate directory can redirect
        a write or mkdir outside the store root.
        """

        try:
            relative = path.relative_to(self.root_dir)
        except ValueError as exc:
            raise MemoryObjectTamperError("memory store path escapes the store root") from exc
        current = self.root_dir
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise MemoryObjectTamperError(
                    "refusing to write through a symlink in the memory store"
                )

    def _content_path(self, content_hash: str) -> Path:
        return self.root_dir / "objects" / content_hash[:2] / f"{content_hash}.bin"

    def _metadata_path(self, memory_ref_id: str) -> Path:
        ref_hash = sha256_hex(memory_ref_id.encode("utf-8"))
        return self.root_dir / "metadata" / ref_hash[:2] / f"{ref_hash}.json"
