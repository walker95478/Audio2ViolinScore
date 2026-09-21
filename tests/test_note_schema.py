from __future__ import annotations

import json

import pytest

from audio2violinscore.notes.schema import (
    CanonicalNoteEvents,
    NoteEvent,
    NoteSchemaError,
    from_basic_pitch_events,
)


def valid_note(**overrides):
    values = {
        "id": 1,
        "pitch_midi": 69,
        "onset_sec": 0.25,
        "offset_sec": 1.25,
        "confidence": 0.9,
        "instrument": "vocals",
        "source": "tone.wav",
        "backend": "basic_pitch",
    }
    values.update(overrides)
    return NoteEvent(**values)


def test_note_and_document_round_trip_is_stable(tmp_path):
    document = CanonicalNoteEvents(
        source={"file": "tone.wav", "stem": "vocals"},
        backend={"name": "basic_pitch", "device": "cpu"},
        notes=(valid_note(),),
        tempo=None,
        warnings=("synthetic input",),
        extensions={"future": {"pitch_bend": "preserved"}},
    )
    path = tmp_path / "notes.json"
    document.write_json(path)

    loaded = CanonicalNoteEvents.read_json(path)

    assert loaded.to_dict() == document.to_dict()
    assert loaded.to_json() == document.to_json()
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 1


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"pitch_midi": -1}, "pitch_midi must be an integer"),
        ({"pitch_midi": 128}, "pitch_midi must be an integer"),
        ({"onset_sec": -0.1}, "onset_sec must be >= 0"),
        ({"offset_sec": 0.25}, "offset_sec must be > onset_sec"),
        ({"confidence": 1.1}, r"confidence must be in \[0, 1\]"),
        ({"offset_sec": float("nan")}, "offset_sec must be finite"),
    ],
)
def test_note_boundaries_are_rejected(overrides, message):
    with pytest.raises(NoteSchemaError, match=message):
        valid_note(**overrides)


def test_duplicate_note_ids_are_rejected():
    with pytest.raises(NoteSchemaError, match="note ids must be unique"):
        CanonicalNoteEvents(
            source={"file": "tone.wav"},
            backend={"name": "basic_pitch"},
            notes=(valid_note(id=1), valid_note(id=1, pitch_midi=70)),
        )


def test_basic_pitch_mapping_preserves_pitch_bend_extension():
    document = from_basic_pitch_events(
        [(0.0, 0.5, 69, 0.8, [0.0, 0.1])],
        source="vocals.wav",
    )

    note = document.notes[0]
    assert note.pitch_midi == 69
    assert note.extensions["pitch_bend"] == [0.0, 0.1]
    assert document.source["stem"] == "vocals"