from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import worker


def test_canonical_document_has_stable_relative_metadata():
    document = worker._canonical_document(
        [(0.0, 0.5, 69, 0.8, [0.0])],
        source_name="tone.wav",
        backend={"name": "basic_pitch", "device": "cpu"},
    )

    assert document["schema_version"] == 1
    assert document["source"] == {"file": "tone.wav", "stem": "vocals"}
    assert document["notes"][0]["pitch_midi"] == 69
    assert document["extensions"]["raw_note_events"].startswith("raw/")


def test_worker_request_validation_rejects_relative_paths(tmp_path):
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "request_id": "x",
                "operation": "transcribe",
                "input": {"audio_path": "tone.wav"},
                "options": {"model": "htdemucs", "target_stem": "vocals", "device": "cpu"},
                "output_dir": str(tmp_path / "out"),
            }
        ),
        encoding="utf-8",
    )

    try:
        worker._load_request(request)
    except worker.WorkerInputError as exc:
        assert "absolute" in str(exc)
    else:
        raise AssertionError("relative audio path was accepted")