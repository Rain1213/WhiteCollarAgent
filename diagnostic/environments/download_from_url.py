"""Diagnostic environment for the "download from url" action."""
from __future__ import annotations

import types
from pathlib import Path
from typing import Any, Mapping, Tuple

from diagnostic.framework import ActionTestCase, ExecutionResult, PreparedEnv


DOWNLOAD_URL = "https://example.com/resource.bin"
PAYLOAD_BYTES = b"diagnostic download payload"


def _build_httpx_stub(expected_url: str, payload: bytes) -> types.ModuleType:
    module = types.ModuleType("httpx")

    class _FakeStream:
        def __init__(self, data: bytes) -> None:
            self._data = data

        async def __aenter__(self) -> _FakeStream:  # type: ignore[name-defined]
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
            return False

        def raise_for_status(self) -> None:
            pass

        async def aiter_bytes(self, chunk_size: int):  # noqa: ARG002, D401
            yield self._data

    class AsyncClient:  # noqa: D401 - behaviour mirrors httpx.AsyncClient
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, D401
            pass

        async def __aenter__(self) -> AsyncClient:  # type: ignore[name-defined]
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
            return False

        def stream(self, method: str, url: str, **kwargs) -> _FakeStream:
            if method != "GET":
                raise AssertionError(f"Unexpected method {method!r} in stub")
            if url != expected_url:
                raise AssertionError(
                    f"Unexpected URL {url!r}; expected {expected_url!r}"
                )
            return _FakeStream(payload)

    module.AsyncClient = AsyncClient
    return module


def prepare_download_from_url(tmp_path: Path, action: Mapping[str, Any]) -> PreparedEnv:  # noqa: ARG001
    dest_dir = tmp_path / "downloads"
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = "sample.bin"
    expected_path = dest_dir / filename

    httpx_stub = _build_httpx_stub(DOWNLOAD_URL, PAYLOAD_BYTES)

    return PreparedEnv(
        input_overrides={
            "url": DOWNLOAD_URL,
            "dest_dir": str(dest_dir),
            "filename": filename,
        },
        extra_modules={"httpx": httpx_stub},
        context={
            "expected_path": str(expected_path),
            "expected_bytes": PAYLOAD_BYTES,
        },
    )


def validate_download_from_url(
    result: ExecutionResult,
    input_data: Mapping[str, Any],  # noqa: ARG001
    context: Mapping[str, Any],
) -> Tuple[str, str]:
    output = result.parsed_output or {}
    if not isinstance(output, Mapping):
        return "incorrect result", "Expected JSON object output."

    if output.get("status") != "ok":
        return "error", f"Action reported failure: {output}"

    expected_path = context.get("expected_path")
    if output.get("path") != expected_path:
        return (
            "incorrect result",
            f"Path mismatch. expected={expected_path} actual={output.get('path')}",
        )

    expected_bytes: bytes = context.get("expected_bytes", b"")
    written_path = Path(expected_path)
    if not written_path.exists():
        return "error", "Downloaded file was not created."

    actual_bytes = written_path.read_bytes()
    if actual_bytes != expected_bytes:
        return "incorrect result", "File contents differ from expected payload."

    if output.get("size_bytes") != len(expected_bytes):
        return "incorrect result", "Reported size does not match payload length."

    return "passed", "File downloaded with expected contents."


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="download from url",
        base_input={},
        prepare=prepare_download_from_url,
        validator=validate_download_from_url,
    )
