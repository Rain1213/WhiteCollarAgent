"""Diagnostic environment for the "screenshot" action."""

from __future__ import annotations

import types
from pathlib import Path
from typing import Any, Mapping

from diagnostic.framework import ActionTestCase, ExecutionResult, PreparedEnv


def _build_mss_stub(pixel_bytes: bytes) -> types.ModuleType:
    module = types.ModuleType("mss")

    class _Shot:
        def __init__(self) -> None:
            self.size = (2, 2)
            self.rgb = pixel_bytes

    class _MSS:
        def __init__(self) -> None:
            self.monitors = [None]

        def __enter__(self) -> "_MSS":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:  # noqa: ANN401
            return False

        def grab(self, monitor: Any) -> _Shot:  # noqa: ANN401
            return _Shot()

    module.mss = _MSS  # type: ignore[attr-defined]
    return module


def _build_pillow_stub(written_files: list[Path]) -> dict[str, types.ModuleType]:
    module = types.ModuleType("PIL")
    image_module = types.ModuleType("PIL.Image")

    class _Image:
        def __init__(self, data: bytes) -> None:
            self._data = data

        def save(self, path: str, fmt: str) -> None:
            file_path = Path(path)
            file_path.write_bytes(b"PNG" + self._data)
            written_files.append(file_path)

    def frombytes(mode: str, size: tuple[int, int], data: bytes) -> _Image:  # noqa: ANN401
        if mode != "RGB":
            raise ValueError("Expected RGB mode for stub image.")
        if size != (2, 2):
            raise ValueError("Unexpected image dimensions.")
        return _Image(data)

    image_module.frombytes = frombytes  # type: ignore[attr-defined]
    module.Image = image_module  # type: ignore[attr-defined]
    pillow_pkg = types.ModuleType("Pillow")
    pillow_pkg.Image = image_module  # type: ignore[attr-defined]
    return {"PIL": module, "PIL.Image": image_module, "Pillow": pillow_pkg}


def get_test_case() -> ActionTestCase:
    def prepare(tmp_path: Path, action: Mapping[str, Any]) -> PreparedEnv:  # noqa: ARG001
        output_path = tmp_path / "captures" / "screen.png"
        output_path.parent.mkdir(parents=True)

        written: list[Path] = []
        extra_modules = {"mss": _build_mss_stub(pixel_bytes=b"\x00\x01\x02\x03" * 1)}
        extra_modules.update(_build_pillow_stub(written))

        return PreparedEnv(
            input_overrides={
                "output_path": str(output_path),
                "format": "png",
            },
            extra_modules=extra_modules,
            context={
                "output_path": output_path,
                "written": written,
            },
        )

    def validator(
        result: ExecutionResult,
        input_data: Mapping[str, Any],
        context: Mapping[str, Any],
    ) -> tuple[str, str]:
        if result.has_error():
            return "error", "Execution raised an exception."

        payload = result.parsed_output or {}
        if payload.get("status") != "success":
            return "incorrect result", f"Unexpected status: {payload.get('status')!r}."
        if payload.get("file_path") != str(context["output_path"]):
            return "incorrect result", "file_path did not match requested output path."
        if payload.get("message") not in ("", None):
            return "incorrect result", "Message should be empty for successful capture."

        written: list[Path] = context["written"]
        if written != [context["output_path"]]:
            return "incorrect result", "Screenshot stub did not record expected save path."
        if not context["output_path"].is_file():
            return "incorrect result", "Screenshot file was not created."
        data = context["output_path"].read_bytes()
        if not data.startswith(b"PNG\x00\x01"):
            return "incorrect result", "Screenshot payload did not contain stub signature."

        return "passed", "Screenshot captured using stub modules."

    return ActionTestCase(
        name="screenshot",
        base_input={},
        prepare=prepare,
        validator=validator,
    )
