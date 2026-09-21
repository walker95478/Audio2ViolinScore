"""Versioned JSON protocol shared by Core and isolated workers."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
VALID_STATUSES = frozenset({"success", "partial", "failed"})


class ProtocolError(ValueError):
    """Raised when a protocol document is malformed or unsupported."""


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ProtocolError(f"{field} must be a JSON object")
    return dict(value)


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProtocolError(f"{field} must be a non-empty string")
    return value


def _schema_version(value: Any) -> int:
    if isinstance(value, bool) or value != SCHEMA_VERSION:
        raise ProtocolError(f"unsupported schema_version: {value!r}")
    return SCHEMA_VERSION


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProtocolError(f"JSON file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"malformed JSON in {path}: {exc.msg}") from exc
    return _mapping(value, str(path))


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


@dataclass(frozen=True)
class TranscriptionRequest:
    request_id: str
    audio_path: str
    output_dir: str
    options: dict[str, Any]
    schema_version: int = SCHEMA_VERSION
    operation: str = "transcribe"

    def __post_init__(self) -> None:
        _schema_version(self.schema_version)
        _string(self.request_id, "request_id")
        if self.operation != "transcribe":
            raise ProtocolError("operation must be 'transcribe'")
        _string(self.audio_path, "input.audio_path")
        _string(self.output_dir, "output_dir")
        if not isinstance(self.options, dict):
            raise ProtocolError("options must be a JSON object")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "operation": self.operation,
            "input": {"audio_path": self.audio_path},
            "options": dict(self.options),
            "output_dir": self.output_dir,
        }

    def write_json(self, path: Path) -> None:
        _write_json(path, self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> TranscriptionRequest:
        data = _mapping(value, "request")
        schema_version = _schema_version(data.get("schema_version"))
        input_data = _mapping(data.get("input"), "input")
        return cls(
            request_id=_string(data.get("request_id"), "request_id"),
            audio_path=_string(input_data.get("audio_path"), "input.audio_path"),
            output_dir=_string(data.get("output_dir"), "output_dir"),
            options=_mapping(data.get("options", {}), "options"),
            schema_version=schema_version,
            operation=data.get("operation"),
        )

    @classmethod
    def read_json(cls, path: Path) -> TranscriptionRequest:
        return cls.from_dict(_read_json(path))


@dataclass(frozen=True)
class WorkerErrorInfo:
    code: str
    stage: str
    message: str
    recovery: str | None = None

    def __post_init__(self) -> None:
        _string(self.code, "error.code")
        _string(self.stage, "error.stage")
        _string(self.message, "error.message")
        if self.recovery is not None:
            _string(self.recovery, "error.recovery")

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "code": self.code,
            "stage": self.stage,
            "message": self.message,
        }
        if self.recovery is not None:
            value["recovery"] = self.recovery
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> WorkerErrorInfo:
        data = _mapping(value, "error")
        return cls(
            code=_string(data.get("code"), "error.code"),
            stage=_string(data.get("stage"), "error.stage"),
            message=_string(data.get("message"), "error.message"),
            recovery=data.get("recovery"),
        )


@dataclass
class WorkerResult:
    request_id: str
    status: str
    backend: dict[str, Any]
    artifacts: dict[str, Any]
    notes: dict[str, Any] | None
    warnings: list[str]
    error: WorkerErrorInfo | None = None
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _schema_version(self.schema_version)
        _string(self.request_id, "request_id")
        if self.status not in VALID_STATUSES:
            raise ProtocolError(f"unsupported worker status: {self.status!r}")
        if not isinstance(self.backend, dict):
            raise ProtocolError("backend must be a JSON object")
        if not isinstance(self.artifacts, dict):
            raise ProtocolError("artifacts must be a JSON object")
        if self.notes is not None and not isinstance(self.notes, dict):
            raise ProtocolError("notes must be a JSON object or null")
        if not isinstance(self.warnings, list) or not all(
            isinstance(item, str) for item in self.warnings
        ):
            raise ProtocolError("warnings must be a list of strings")
        if self.error is not None and not isinstance(self.error, WorkerErrorInfo):
            raise ProtocolError("error must be a WorkerErrorInfo object or null")
        if self.status == "failed" and self.error is None:
            raise ProtocolError("failed result must include error")
        if self.status == "success" and self.error is not None:
            raise ProtocolError("success result cannot include error")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "status": self.status,
            "backend": dict(self.backend),
            "artifacts": dict(self.artifacts),
            "notes": self.notes,
            "warnings": list(self.warnings),
            "error": self.error.to_dict() if self.error else None,
        }

    def write_json(self, path: Path) -> None:
        _write_json(path, self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> WorkerResult:
        data = _mapping(value, "result")
        error_value = data.get("error")
        return cls(
            request_id=_string(data.get("request_id"), "request_id"),
            status=_string(data.get("status"), "status"),
            backend=_mapping(data.get("backend", {}), "backend"),
            artifacts=_mapping(data.get("artifacts", {}), "artifacts"),
            notes=(None if data.get("notes") is None else _mapping(data["notes"], "notes")),
            warnings=data.get("warnings", []),
            error=(None if error_value is None else WorkerErrorInfo.from_dict(error_value)),
            schema_version=_schema_version(data.get("schema_version")),
        )

    @classmethod
    def read_json(cls, path: Path) -> WorkerResult:
        return cls.from_dict(_read_json(path))