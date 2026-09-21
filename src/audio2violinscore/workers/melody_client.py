"""Subprocess client for the isolated Melody Worker."""

from __future__ import annotations

import os
import subprocess
import uuid
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .protocol import ProtocolError, TranscriptionRequest, WorkerResult


class MelodyClientError(RuntimeError):
    """Base error for worker transport and structured result failures."""


class WorkerUnavailableError(MelodyClientError):
    pass


class WorkerInputError(MelodyClientError):
    pass


class WorkerTimeoutError(MelodyClientError):
    pass


class WorkerProcessError(MelodyClientError):
    pass


class WorkerResultError(MelodyClientError):
    pass


class WorkerFailedError(MelodyClientError):
    def __init__(self, result: WorkerResult):
        self.result = result
        error = result.error
        detail = error.code if error else "worker_failed"
        super().__init__(f"Melody Worker failed: {detail}")


Runner = Callable[..., subprocess.CompletedProcess[str]]


def _captured_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _write_log(path: Path, value: str | bytes | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_captured_text(value), encoding="utf-8")


class MelodyClient:
    """Launch Melody Worker through a strict JSON-file subprocess boundary."""

    def __init__(
        self,
        project_root: Path | None = None,
        *,
        timeout_seconds: float = 1800,
        worker_python: Path | None = None,
        worker_script: Path | None = None,
        runner: Runner = subprocess.run,
    ) -> None:
        self.project_root = (project_root or Path.cwd()).resolve()
        worker_root = self.project_root / "workers" / "melody"
        self.worker_python = worker_python or worker_root / ".venv" / "Scripts" / "python.exe"
        self.worker_script = worker_script or worker_root / "worker.py"
        self.run_root = self.project_root / "temp" / "melody-runs"
        self.output_root = self.project_root / "output" / "melody"
        self.timeout_seconds = timeout_seconds
        self._runner = runner

    def _check_worker(self) -> None:
        missing = [
            path
            for path in (self.worker_python, self.worker_script)
            if not path.is_file()
        ]
        if missing:
            names = ", ".join(str(path) for path in missing)
            raise WorkerUnavailableError(f"Melody Worker is unavailable: {names}")

    def _options(self, options: dict[str, Any] | None) -> dict[str, Any]:
        merged: dict[str, Any] = {
            "model": "htdemucs",
            "target_stem": "vocals",
            "device": "cpu",
        }
        if options:
            merged.update(options)
        if merged.get("model") != "htdemucs":
            raise WorkerInputError("Phase 1B only supports model='htdemucs'")
        if merged.get("target_stem") != "vocals":
            raise WorkerInputError("Phase 1B only supports target_stem='vocals'")
        if merged.get("device") != "cpu":
            raise WorkerInputError("Phase 1B only supports device='cpu'")
        return merged

    def run(
        self,
        audio_path: str | Path,
        *,
        options: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> WorkerResult:
        self._check_worker()
        audio = Path(audio_path).expanduser().resolve()
        if not audio.is_file():
            raise WorkerInputError(f"audio input does not exist: {audio}")

        request_id = uuid.uuid4().hex
        run_dir = self.run_root / request_id
        output_dir = self.output_root / request_id
        request_path = run_dir / "request.json"
        result_path = run_dir / "result.json"
        stdout_path = run_dir / "logs" / "worker.stdout.log"
        stderr_path = run_dir / "logs" / "worker.stderr.log"
        request = TranscriptionRequest(
            request_id=request_id,
            audio_path=str(audio),
            output_dir=str(output_dir),
            options=self._options(options),
        )
        request.write_json(request_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["TORCH_HOME"] = str(self.project_root / "cache" / "torch")
        env["A2VS_MODEL_CACHE"] = str(self.project_root / "cache" / "melody")
        command: Sequence[str] = (
            str(self.worker_python),
            str(self.worker_script),
            "--request",
            str(request_path),
            "--result",
            str(result_path),
        )
        try:
            completed = self._runner(
                list(command),
                cwd=str(self.project_root),
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                timeout=timeout_seconds or self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            _write_log(stdout_path, exc.stdout)
            _write_log(stderr_path, exc.stderr)
            raise WorkerTimeoutError(
                f"Melody Worker timed out after {timeout_seconds or self.timeout_seconds}s; "
                f"logs: {stderr_path}"
            ) from exc
        except OSError as exc:
            raise WorkerProcessError(f"could not start Melody Worker: {type(exc).__name__}") from exc

        _write_log(stdout_path, completed.stdout)
        _write_log(stderr_path, completed.stderr)
        if not result_path.is_file():
            raise WorkerProcessError(
                f"Melody Worker did not write result.json (exit={completed.returncode}); "
                f"logs: {stderr_path}"
            )
        try:
            result = WorkerResult.read_json(result_path)
        except (OSError, ProtocolError) as exc:
            raise WorkerResultError(f"invalid Melody Worker result: {type(exc).__name__}") from exc
        if result.request_id != request_id:
            raise WorkerResultError("Melody Worker result request_id does not match")

        result.artifacts.setdefault(
            "worker_stdout_log",
            {"kind": "log", "path": stdout_path.relative_to(self.project_root).as_posix()},
        )
        result.artifacts.setdefault(
            "worker_stderr_log",
            {"kind": "log", "path": stderr_path.relative_to(self.project_root).as_posix()},
        )
        if result.status == "failed":
            raise WorkerFailedError(result)
        if result.status == "partial":
            return result
        if completed.returncode != 0:
            raise WorkerProcessError(
                f"Melody Worker exited with code {completed.returncode}; logs: {stderr_path}"
            )
        return result