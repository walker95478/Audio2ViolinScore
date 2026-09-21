"""Isolated Melody Worker: Demucs vocals separation and Basic Pitch transcription.

This module deliberately does not import the Core package. It communicates with
Core through UTF-8 JSON request/result files and keeps all backend imports inside
the worker process.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import os
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
WORKER_VERSION = "0.1.0"
WORKER_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = WORKER_ROOT.parents[1]
MELODY_CACHE = PROJECT_ROOT / "cache" / "melody"
TORCH_CACHE = PROJECT_ROOT / "cache" / "torch"
SUPPORTED_MODEL = "htdemucs"
SUPPORTED_STEM = "vocals"
SUPPORTED_DEVICE = "cpu"


class WorkerInputError(ValueError):
    """Raised for invalid worker request data."""


def _configure_environment() -> None:
    MELODY_CACHE.mkdir(parents=True, exist_ok=True)
    TORCH_CACHE.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TORCH_HOME", str(TORCH_CACHE))
    os.environ.setdefault("A2VS_MODEL_CACHE", str(MELODY_CACHE))
    os.environ.setdefault("HF_HOME", str(MELODY_CACHE / "huggingface"))
    os.environ.setdefault("HF_HUB_CACHE", str(MELODY_CACHE / "huggingface" / "hub"))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(MELODY_CACHE / "huggingface" / "hub"))
    os.environ.setdefault("NUMBA_CACHE_DIR", str(MELODY_CACHE / "numba"))


def _package_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def _version_report() -> dict[str, Any]:
    _configure_environment()
    import basic_pitch
    import demucs
    import onnxruntime
    import soundfile
    import torch

    del basic_pitch, demucs, soundfile
    return {
        "worker_version": WORKER_VERSION,
        "python": sys.version.split()[0],
        "python_executable": str(Path(sys.executable).resolve()),
        "packages": {
            "demucs": _package_version("demucs"),
            "basic_pitch": _package_version("basic-pitch"),
            "torch": _package_version("torch"),
            "onnxruntime": _package_version("onnxruntime"),
            "soundfile": _package_version("soundfile"),
        },
        "device": SUPPORTED_DEVICE,
        "torch_cuda_available": bool(torch.cuda.is_available()),
        "onnxruntime_providers": list(onnxruntime.get_available_providers()),
        "model_cache": "cache/melody",
        "torch_cache": "cache/torch",
    }


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _safe_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value
    if isinstance(value, Mapping):
        return {str(key): _safe_json_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_safe_json_value(item) for item in value]
    if hasattr(value, "tolist"):
        return _safe_json_value(value.tolist())
    return str(value)


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkerInputError(f"{field} must be a non-empty string")
    return value


def _load_request(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkerInputError("request JSON does not exist") from exc
    except json.JSONDecodeError as exc:
        raise WorkerInputError(f"request JSON is malformed: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise WorkerInputError("request must be a JSON object")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise WorkerInputError("unsupported request schema_version")
    request_id = _require_string(value.get("request_id"), "request_id")
    if value.get("operation") != "transcribe":
        raise WorkerInputError("operation must be 'transcribe'")
    input_data = value.get("input")
    if not isinstance(input_data, dict):
        raise WorkerInputError("input must be a JSON object")
    audio_path = Path(_require_string(input_data.get("audio_path"), "input.audio_path"))
    output_dir = Path(_require_string(value.get("output_dir"), "output_dir"))
    if not audio_path.is_absolute():
        raise WorkerInputError("input.audio_path must be absolute")
    if not output_dir.is_absolute():
        raise WorkerInputError("output_dir must be absolute")
    options = value.get("options")
    if not isinstance(options, dict):
        raise WorkerInputError("options must be a JSON object")
    if options.get("model", SUPPORTED_MODEL) != SUPPORTED_MODEL:
        raise WorkerInputError("only model='htdemucs' is supported")
    if options.get("target_stem", SUPPORTED_STEM) != SUPPORTED_STEM:
        raise WorkerInputError("only target_stem='vocals' is supported")
    if options.get("device", SUPPORTED_DEVICE) != SUPPORTED_DEVICE:
        raise WorkerInputError("only device='cpu' is supported")
    if not audio_path.is_file():
        raise WorkerInputError("input audio file does not exist")
    value["request_id"] = request_id
    value["audio_path"] = str(audio_path)
    value["output_dir"] = str(output_dir)
    return value


def _error(
    code: str,
    stage: str,
    message: str,
    recovery: str,
) -> dict[str, str]:
    return {
        "code": code,
        "stage": stage,
        "message": message,
        "recovery": recovery,
    }


def _artifact(path: Path, output_dir: Path, kind: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "path": path.relative_to(output_dir).as_posix(),
        "bytes": path.stat().st_size,
    }


def _normalise_note_event(event: Any) -> dict[str, Any]:
    if isinstance(event, Mapping):
        onset = event.get("onset_sec", event.get("start_time"))
        offset = event.get("offset_sec", event.get("end_time"))
        pitch = event.get("pitch_midi", event.get("midi"))
        amplitude = event.get("confidence", event.get("amplitude"))
        pitch_bend = event.get("pitch_bend", event.get("pitch_bends"))
    else:
        values = list(event)
        if len(values) < 4:
            raise ValueError("Basic Pitch note event has fewer than four values")
        onset, offset, pitch, amplitude = values[:4]
        pitch_bend = values[4] if len(values) > 4 else None
    onset_value = float(onset)
    offset_value = float(offset)
    pitch_value = int(round(float(pitch)))
    confidence = float(amplitude)
    if not math.isfinite(onset_value) or not math.isfinite(offset_value):
        raise ValueError("Basic Pitch note event has non-finite timing")
    if not 0 <= pitch_value <= 127:
        raise ValueError("Basic Pitch note event pitch is outside MIDI range")
    if onset_value < 0 or offset_value <= onset_value:
        raise ValueError("Basic Pitch note event has invalid timing")
    if not 0 <= confidence <= 1:
        raise ValueError("Basic Pitch note event confidence is outside [0, 1]")
    extensions: dict[str, Any] = {}
    if pitch_bend is not None:
        extensions["pitch_bend"] = _safe_json_value(pitch_bend)
    return {
        "onset_sec": onset_value,
        "offset_sec": offset_value,
        "pitch_midi": pitch_value,
        "confidence": confidence,
        "extensions": extensions,
    }


def _canonical_document(
    events: Sequence[Any],
    *,
    source_name: str,
    backend: Mapping[str, Any],
) -> dict[str, Any]:
    notes: list[dict[str, Any]] = []
    for index, event in enumerate(events, start=1):
        normalised = _normalise_note_event(event)
        notes.append(
            {
                "id": index,
                **normalised,
                "instrument": "vocals",
                "source": source_name,
                "backend": "basic_pitch",
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "source": {"file": source_name, "stem": SUPPORTED_STEM},
        "backend": dict(backend),
        "notes": notes,
        "tempo": None,
        "warnings": [] if notes else ["basic_pitch_returned_no_notes"],
        "extensions": {"raw_note_events": "raw/basic_pitch_note_events.json"},
    }


def _metadata(
    *,
    request: Mapping[str, Any],
    versions: Mapping[str, Any],
    timings: Mapping[str, float],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "worker_version": WORKER_VERSION,
        "request_id": request["request_id"],
        "device": SUPPORTED_DEVICE,
        "model": request["options"].get("model", SUPPORTED_MODEL),
        "target_stem": SUPPORTED_STEM,
        "versions": dict(versions),
        "timings_sec": dict(timings),
        "cache_roots": {"melody": "cache/melody", "torch": "cache/torch"},
    }


def _separate_vocals(
    audio_path: Path,
    vocals_path: Path,
    *,
    model: str,
) -> None:
    from demucs.api import Separator, save_audio

    separator = Separator(model=model, device=SUPPORTED_DEVICE, progress=False, jobs=0)
    _, separated = separator.separate_audio_file(audio_path)
    if SUPPORTED_STEM not in separated:
        raise RuntimeError("Demucs did not return the vocals stem")
    vocals_path.parent.mkdir(parents=True, exist_ok=True)
    save_audio(
        separated[SUPPORTED_STEM].cpu(),
        vocals_path,
        samplerate=separator.samplerate,
    )


def _transcribe_vocals(
    vocals_path: Path,
    midi_path: Path,
) -> tuple[Sequence[Any], dict[str, Any]]:
    from basic_pitch import ICASSP_2022_MODEL_PATH
    from basic_pitch.inference import predict

    _, midi_data, note_events = predict(
        str(vocals_path),
        model_or_model_path=ICASSP_2022_MODEL_PATH,
    )
    midi_path.parent.mkdir(parents=True, exist_ok=True)
    midi_data.write(str(midi_path))
    versions = {
        "demucs": _package_version("demucs"),
        "basic_pitch": _package_version("basic-pitch"),
        "torch": _package_version("torch"),
        "onnxruntime": _package_version("onnxruntime"),
        "soundfile": _package_version("soundfile"),
    }
    return note_events, versions


def _run_request(request_path: Path, result_path: Path) -> int:
    request_id = "unknown"
    output_dir: Path | None = None
    try:
        request = _load_request(request_path)
        request_id = str(request["request_id"])
        output_dir = Path(request["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        stems_dir = output_dir / "stems"
        raw_dir = output_dir / "raw"
        canonical_dir = output_dir / "canonical"
        logs_dir = output_dir / "logs"
        for directory in (stems_dir, raw_dir, canonical_dir, logs_dir):
            directory.mkdir(parents=True, exist_ok=True)

        started = time.perf_counter()
        _version_report()
        vocals_path = stems_dir / "vocals.wav"
        _separate_vocals(
            Path(request["audio_path"]),
            vocals_path,
            model=request["options"].get("model", SUPPORTED_MODEL),
        )
        demucs_seconds = time.perf_counter() - started

        midi_path = raw_dir / "basic_pitch.mid"
        note_events, backend_versions = _transcribe_vocals(vocals_path, midi_path)
        basic_pitch_seconds = time.perf_counter() - started - demucs_seconds
        raw_events_path = raw_dir / "basic_pitch_note_events.json"
        raw_events = [_safe_json_value(event) for event in note_events]
        _write_json(raw_events_path, {"note_events": raw_events})

        backend = {
            "name": "basic_pitch",
            "demucs_model": request["options"].get("model", SUPPORTED_MODEL),
            "device": SUPPORTED_DEVICE,
            "versions": backend_versions,
        }
        canonical = _canonical_document(
            note_events,
            source_name=Path(request["audio_path"]).name,
            backend=backend,
        )
        canonical_path = canonical_dir / "notes.json"
        _write_json(canonical_path, canonical)
        total_seconds = time.perf_counter() - started
        metadata_path = output_dir / "worker_metadata.json"
        _write_json(
            metadata_path,
            _metadata(
                request=request,
                versions=backend_versions,
                timings={
                    "demucs_sec": round(demucs_seconds, 3),
                    "basic_pitch_sec": round(basic_pitch_seconds, 3),
                    "total_sec": round(total_seconds, 3),
                },
            ),
        )
        (logs_dir / "worker.log").write_text(
            f"status=success\nrequest_id={request_id}\n"
            f"notes={len(canonical['notes'])}\n",
            encoding="utf-8",
        )
        result = {
            "schema_version": SCHEMA_VERSION,
            "request_id": request_id,
            "status": "success",
            "backend": backend,
            "artifacts": {
                "vocals_stem": _artifact(vocals_path, output_dir, "audio"),
                "raw_midi": _artifact(midi_path, output_dir, "midi"),
                "raw_note_events": _artifact(raw_events_path, output_dir, "json"),
                "canonical_notes": _artifact(canonical_path, output_dir, "json"),
                "metadata": _artifact(metadata_path, output_dir, "json"),
                "worker_log": _artifact(logs_dir / "worker.log", output_dir, "log"),
            },
            "notes": canonical,
            "warnings": canonical["warnings"],
            "error": None,
        }
        _write_json(result_path, result)
        print(f"Melody Worker success: {len(canonical['notes'])} note events")
        return 0
    except WorkerInputError as exc:
        result = {
            "schema_version": SCHEMA_VERSION,
            "request_id": request_id,
            "status": "failed",
            "backend": {"name": "melody_worker", "device": SUPPORTED_DEVICE},
            "artifacts": {},
            "notes": None,
            "warnings": [],
            "error": _error(
                "invalid_request",
                "request",
                str(exc),
                "Validate absolute paths, schema_version=1, and CPU options.",
            ),
        }
        _write_json(result_path, result)
        return 1
    except Exception as exc:
        stage = "demucs" if output_dir and not (output_dir / "stems" / "vocals.wav").is_file() else "basic_pitch"
        status = "failed" if stage == "demucs" else "partial"
        artifacts: dict[str, Any] = {}
        if output_dir and (output_dir / "stems" / "vocals.wav").is_file():
            artifacts["vocals_stem"] = _artifact(
                output_dir / "stems" / "vocals.wav",
                output_dir,
                "audio",
            )
        if output_dir:
            (output_dir / "logs").mkdir(parents=True, exist_ok=True)
            (output_dir / "logs" / "worker.log").write_text(
                f"status={status}\nrequest_id={request_id}\nstage={stage}\n",
                encoding="utf-8",
            )
        result = {
            "schema_version": SCHEMA_VERSION,
            "request_id": request_id,
            "status": status,
            "backend": {"name": "melody_worker", "device": SUPPORTED_DEVICE},
            "artifacts": artifacts,
            "notes": None,
            "warnings": ["backend_stage_failed"],
            "error": _error(
                f"{stage}_failed",
                stage,
                f"{type(exc).__name__}: {str(exc)[:240]}",
                "Inspect worker stderr and verify the isolated CPU environment.",
            ),
        }
        _write_json(result_path, result)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="melody-worker")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--request", type=Path)
    parser.add_argument("--result", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.version:
        try:
            report = _version_report()
        except Exception as exc:
            report = {
                "worker_version": WORKER_VERSION,
                "status": "broken",
                "error": {
                    "code": "import_failed",
                    "stage": "version",
                    "message": f"{type(exc).__name__}: {str(exc)[:240]}",
                },
            }
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
        report["status"] = "pass"
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(
                f"Melody Worker {WORKER_VERSION} "
                f"demucs={report['packages']['demucs']} "
                f"basic_pitch={report['packages']['basic_pitch']} "
                f"torch={report['packages']['torch']}"
            )
        return 0
    if args.request is None or args.result is None:
        return 2
    return _run_request(args.request.resolve(), args.result.resolve())


if __name__ == "__main__":
    raise SystemExit(main())