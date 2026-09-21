from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from audio2violinscore.workers.melody_client import (
    MelodyClient,
    WorkerFailedError,
    WorkerInputError,
    WorkerProcessError,
    WorkerResultError,
    WorkerTimeoutError,
    WorkerUnavailableError,
)


def make_client(tmp_path: Path, runner):
    worker_root = tmp_path / "workers" / "melody"
    environment = worker_root / ".venv" / "Scripts"
    environment.mkdir(parents=True)
    (environment / "python.exe").write_text("fake", encoding="utf-8")
    (worker_root / "worker.py").write_text("# fake worker", encoding="utf-8")
    audio = tmp_path / "中文" / "tone.wav"
    audio.parent.mkdir()
    audio.write_bytes(b"RIFF")
    client = MelodyClient(
        tmp_path,
        worker_python=environment / "python.exe",
        worker_script=worker_root / "worker.py",
        runner=runner,
        timeout_seconds=2,
    )
    return client, audio


def success_runner(calls):
    def runner(args, **kwargs):
        calls.append((args, kwargs))
        request = json.loads(Path(args[args.index("--request") + 1]).read_text(encoding="utf-8"))
        result_path = Path(args[args.index("--result") + 1])
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "request_id": request["request_id"],
                    "status": "success",
                    "backend": {"name": "test"},
                    "artifacts": {},
                    "notes": {"schema_version": 1, "notes": []},
                    "warnings": [],
                    "error": None,
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    return runner


def test_client_success_uses_safe_subprocess_and_unicode_path(tmp_path):
    calls = []
    client, audio = make_client(tmp_path, success_runner(calls))

    result = client.run(audio)

    assert result.status == "success"
    assert calls[0][1]["shell"] is False
    assert calls[0][1]["cwd"] == str(tmp_path.resolve())
    assert calls[0][0][0].endswith("python.exe")
    assert "worker_stdout_log" in result.artifacts
    assert "worker_stderr_log" in result.artifacts


def test_client_rejects_non_cpu_options(tmp_path):
    client, audio = make_client(tmp_path, lambda *_args, **_kwargs: None)

    with pytest.raises(WorkerInputError, match="device='cpu'"):
        client.run(audio, options={"device": "cuda"})


def test_client_reports_missing_worker(tmp_path):
    client = MelodyClient(tmp_path)

    with pytest.raises(WorkerUnavailableError):
        client.run(tmp_path / "missing.wav")


def test_client_reports_timeout_and_saves_logs(tmp_path):
    def timeout_runner(_args, **_kwargs):
        raise subprocess.TimeoutExpired("worker", 2, output=b"stdout", stderr=b"stderr")

    client, audio = make_client(tmp_path, timeout_runner)

    with pytest.raises(WorkerTimeoutError):
        client.run(audio)

    assert list((tmp_path / "temp" / "melody-runs").rglob("worker.stderr.log"))


def test_client_reports_missing_result(tmp_path):
    def missing_runner(_args, **_kwargs):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    client, audio = make_client(tmp_path, missing_runner)

    with pytest.raises(WorkerProcessError):
        client.run(audio)


def test_client_reports_malformed_result(tmp_path):
    def malformed_runner(args, **_kwargs):
        result_path = Path(args[args.index("--result") + 1])
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text("{", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    client, audio = make_client(tmp_path, malformed_runner)

    with pytest.raises(WorkerResultError):
        client.run(audio)


def test_client_reports_schema_and_request_mismatch(tmp_path):
    def mismatch_runner(args, **_kwargs):
        result_path = Path(args[args.index("--result") + 1])
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "request_id": "wrong",
                    "status": "success",
                    "backend": {},
                    "artifacts": {},
                    "notes": None,
                    "warnings": [],
                    "error": None,
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    client, audio = make_client(tmp_path, mismatch_runner)

    with pytest.raises(WorkerResultError, match="invalid Melody Worker result"):
        client.run(audio)


def test_client_propagates_failed_result(tmp_path):
    def failed_runner(args, **_kwargs):
        request = json.loads(Path(args[args.index("--request") + 1]).read_text(encoding="utf-8"))
        result_path = Path(args[args.index("--result") + 1])
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "request_id": request["request_id"],
                    "status": "failed",
                    "backend": {"name": "test"},
                    "artifacts": {},
                    "notes": None,
                    "warnings": [],
                    "error": {
                        "code": "demucs_failed",
                        "stage": "demucs",
                        "message": "failure",
                        "recovery": "retry",
                    },
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=1, stdout="", stderr="worker failure")

    client, audio = make_client(tmp_path, failed_runner)

    with pytest.raises(WorkerFailedError) as exc_info:
        client.run(audio)

    assert exc_info.value.result.error.code == "demucs_failed"


def test_client_rejects_success_result_with_nonzero_exit(tmp_path):
    def nonzero_runner(args, **_kwargs):
        request = json.loads(Path(args[args.index("--request") + 1]).read_text(encoding="utf-8"))
        result_path = Path(args[args.index("--result") + 1])
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "request_id": request["request_id"],
                    "status": "success",
                    "backend": {},
                    "artifacts": {},
                    "notes": None,
                    "warnings": [],
                    "error": None,
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=5, stdout="", stderr="crash")

    client, audio = make_client(tmp_path, nonzero_runner)

    with pytest.raises(WorkerProcessError):
        client.run(audio)
def test_client_returns_structured_partial_result(tmp_path):
    def partial_runner(args, **_kwargs):
        request = json.loads(Path(args[args.index("--request") + 1]).read_text(encoding="utf-8"))
        result_path = Path(args[args.index("--result") + 1])
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "request_id": request["request_id"],
                    "status": "partial",
                    "backend": {"name": "test"},
                    "artifacts": {"vocals_stem": {"path": "stems/vocals.wav"}},
                    "notes": None,
                    "warnings": ["basic pitch unavailable"],
                    "error": {
                        "code": "basic_pitch_failed",
                        "stage": "basic_pitch",
                        "message": "failed after stem separation",
                        "recovery": "inspect stderr",
                    },
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=1, stdout="", stderr="partial")

    client, audio = make_client(tmp_path, partial_runner)

    result = client.run(audio)

    assert result.status == "partial"
    assert result.error.code == "basic_pitch_failed"