"""Canonical Note Events v1, implemented without a runtime schema dependency."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


class NoteSchemaError(ValueError):
    """Raised when Canonical Note Events violate v1 invariants."""


def _number(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise NoteSchemaError(f"{field_name} must be a number")
    value = float(value)
    if not math.isfinite(value):
        raise NoteSchemaError(f"{field_name} must be finite")
    return value


def _text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NoteSchemaError(f"{field_name} must be a non-empty string")
    return value


def _object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise NoteSchemaError(f"{field_name} must be an object")
    return dict(value)


@dataclass(frozen=True)
class NoteEvent:
    id: int
    pitch_midi: int
    onset_sec: float
    offset_sec: float
    confidence: float | None
    instrument: str
    source: str
    backend: str
    extensions: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.id, bool) or not isinstance(self.id, int) or self.id < 1:
            raise NoteSchemaError("id must be a positive integer")
        if (
            isinstance(self.pitch_midi, bool)
            or not isinstance(self.pitch_midi, int)
            or not 0 <= self.pitch_midi <= 127
        ):
            raise NoteSchemaError("pitch_midi must be an integer in [0, 127]")
        onset = _number(self.onset_sec, "onset_sec")
        offset = _number(self.offset_sec, "offset_sec")
        if onset < 0:
            raise NoteSchemaError("onset_sec must be >= 0")
        if offset <= onset:
            raise NoteSchemaError("offset_sec must be > onset_sec")
        if self.confidence is not None:
            confidence = _number(self.confidence, "confidence")
            if not 0 <= confidence <= 1:
                raise NoteSchemaError("confidence must be in [0, 1]")
        _text(self.instrument, "instrument")
        _text(self.source, "source")
        _text(self.backend, "backend")
        if not isinstance(self.extensions, dict):
            raise NoteSchemaError("extensions must be an object")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pitch_midi": self.pitch_midi,
            "onset_sec": self.onset_sec,
            "offset_sec": self.offset_sec,
            "confidence": self.confidence,
            "instrument": self.instrument,
            "source": self.source,
            "backend": self.backend,
            "extensions": dict(self.extensions),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> NoteEvent:
        data = _object(value, "note")
        return cls(
            id=data.get("id"),
            pitch_midi=data.get("pitch_midi"),
            onset_sec=data.get("onset_sec"),
            offset_sec=data.get("offset_sec"),
            confidence=data.get("confidence"),
            instrument=data.get("instrument"),
            source=data.get("source"),
            backend=data.get("backend"),
            extensions=_object(data.get("extensions", {}), "extensions"),
        )


@dataclass(frozen=True)
class CanonicalNoteEvents:
    source: dict[str, Any]
    backend: dict[str, Any]
    notes: tuple[NoteEvent, ...]
    tempo: dict[str, Any] | None = None
    warnings: tuple[str, ...] = ()
    extensions: dict[str, Any] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise NoteSchemaError(f"unsupported schema_version: {self.schema_version!r}")
        if not isinstance(self.source, dict) or not isinstance(self.backend, dict):
            raise NoteSchemaError("source and backend must be objects")
        if self.tempo is not None and not isinstance(self.tempo, dict):
            raise NoteSchemaError("tempo must be an object or null")
        if not isinstance(self.warnings, tuple) or not all(
            isinstance(item, str) for item in self.warnings
        ):
            raise NoteSchemaError("warnings must be a tuple of strings")
        ids = [note.id for note in self.notes]
        if len(ids) != len(set(ids)):
            raise NoteSchemaError("note ids must be unique")
        if not isinstance(self.extensions, dict):
            raise NoteSchemaError("extensions must be an object")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source": dict(self.source),
            "backend": dict(self.backend),
            "notes": [note.to_dict() for note in self.notes],
            "tempo": self.tempo,
            "warnings": list(self.warnings),
            "extensions": dict(self.extensions),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> CanonicalNoteEvents:
        data = _object(value, "canonical note events")
        version = data.get("schema_version")
        if version != SCHEMA_VERSION:
            raise NoteSchemaError(f"unsupported schema_version: {version!r}")
        raw_notes = data.get("notes")
        if not isinstance(raw_notes, list):
            raise NoteSchemaError("notes must be a list")
        warnings = data.get("warnings", [])
        if not isinstance(warnings, list) or not all(isinstance(item, str) for item in warnings):
            raise NoteSchemaError("warnings must be a list of strings")
        return cls(
            source=_object(data.get("source"), "source"),
            backend=_object(data.get("backend"), "backend"),
            notes=tuple(NoteEvent.from_dict(item) for item in raw_notes),
            tempo=(None if data.get("tempo") is None else _object(data["tempo"], "tempo")),
            warnings=tuple(warnings),
            extensions=_object(data.get("extensions", {}), "extensions"),
        )

    @classmethod
    def read_json(cls, path: Path) -> CanonicalNoteEvents:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))


def from_basic_pitch_events(
    events: list[tuple[Any, ...]],
    *,
    source: str,
    instrument: str = "vocals",
    backend: str = "basic_pitch",
) -> CanonicalNoteEvents:
    notes: list[NoteEvent] = []
    for index, event in enumerate(events, start=1):
        if len(event) < 4:
            raise NoteSchemaError("Basic Pitch note event must contain at least four values")
        onset, offset, pitch, amplitude = event[:4]
        pitch_bend = event[4] if len(event) > 4 else None
        extensions = {}
        if pitch_bend is not None:
            extensions["pitch_bend"] = list(pitch_bend)
        notes.append(
            NoteEvent(
                id=index,
                pitch_midi=int(pitch),
                onset_sec=_number(onset, "onset_sec"),
                offset_sec=_number(offset, "offset_sec"),
                confidence=_number(amplitude, "confidence"),
                instrument=instrument,
                source=source,
                backend=backend,
                extensions=extensions,
            )
        )
    return CanonicalNoteEvents(
        source={"file": source, "stem": "vocals"},
        backend={"name": backend},
        notes=tuple(notes),
    )