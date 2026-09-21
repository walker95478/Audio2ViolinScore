from __future__ import annotations

import json

import pytest

from audio2violinscore.workers.protocol import (
    ProtocolError,
    TranscriptionRequest,
    WorkerErrorInfo,
    WorkerResult,
)


def test_request_json_round_trip_with_unicode_paths(tmp_path):
    request = TranscriptionRequest(
        request_id="request-中文",
        audio_path=r"D:\软件\扒谱\temp\中文\input.wav",
        output_dir=r"D:\软件\扒谱\output\melody\request-中文",
        options={"model": "htdemucs", "target_stem": "vocals", "device": "cpu"},
    )
    path = tmp_path / "request.json"
    request.write_json(path)

    loaded = TranscriptionRequest.read_json(path)

    assert loaded == request
    assert json.loads(path.read_text(encoding="utf-8"))["input"]["audio_path"].endswith(
        "input.wav"
    )


def test_result_success_and_partial_round_trip(tmp_path):
    success = WorkerResult(
        request_id="ok",
        status="success",
        backend={"name": "basic_pitch", "device": "cpu"},
        artifacts={"canonical_notes": {"path": "canonical/notes.json"}},
        notes={"schema_version": 1, "notes": []},
        warnings=[],
    )
    partial = WorkerResult(
        request_id="partial",
        status="partial",
        backend={"name": "basic_pitch"},
        artifacts={"vocals_stem": {"path": "stems/vocals.wav"}},
        notes={"schema_version": 1, "notes": []},
        warnings=["raw MIDI unavailable"],
        error=WorkerErrorInfo(
            code="basic_pitch_failed",
            stage="basic_pitch",
            message="backend failed",
            recovery="inspect worker stderr",
        ),
    )
    for expected in (success, partial):
        path = tmp_path / f"{expected.request_id}.json"
        expected.write_json(path)
        assert WorkerResult.read_json(path) == expected


def test_failed_result_requires_structured_error():
    with pytest.raises(ProtocolError, match="failed result must include error"):
        WorkerResult(
            request_id="failed",
            status="failed",
            backend={},
            artifacts={},
            notes=None,
            warnings=[],
        )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"schema_version": 2}, "unsupported schema_version"),
        ({"schema_version": 1, "request_id": "x"}, "input must be a JSON object"),
    ],
)
def test_request_rejects_invalid_documents(payload, message):
    with pytest.raises(ProtocolError, match=message):
        TranscriptionRequest.from_dict(payload)


def test_result_rejects_unknown_status():
    with pytest.raises(ProtocolError, match="unsupported worker status"):
        WorkerResult.from_dict(
            {
                "schema_version": 1,
                "request_id": "x",
                "status": "unknown",
                "backend": {},
                "artifacts": {},
                "notes": None,
                "warnings": [],
                "error": None,
            }
        )