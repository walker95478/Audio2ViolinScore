from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from audio2violinscore import cli, doctor


def fake_runner(args, **_kwargs):
    if len(args) > 1 and args[1] == "-c":
        return SimpleNamespace(returncode=0, stdout="A2VS_UNICODE_OK=True\n", stderr="")
    executable = Path(args[0]).name.lower()
    if executable == "nvidia-smi.exe":
        return SimpleNamespace(
            returncode=0, stdout="RTX 4060 Laptop GPU, 581.80, 8188 MiB\n", stderr=""
        )
    return SimpleNamespace(
        returncode=0, stdout=f"{executable} test version\n", stderr=""
    )


def healthy_which(name: str) -> str | None:
    if name.lower() in {
        "git",
        "ffmpeg",
        "ffmpeg.exe",
        "ffprobe",
        "ffprobe.exe",
        "musescore4.exe",
        "nvidia-smi",
    }:
        return f"C:/fake/{name}"
    return None


def healthy_disk(_drive: str):
    return SimpleNamespace(total=100 * 1024**3, used=80 * 1024**3, free=20 * 1024**3)


@pytest.fixture(autouse=True)
def clear_tool_environment(monkeypatch):
    for name in (
        "A2VS_FFMPEG_PATH",
        "FFMPEG_PATH",
        "A2VS_FFPROBE_PATH",
        "FFPROBE_PATH",
        "A2VS_MUSESCORE_PATH",
        "MUSESCORE_PATH",
    ):
        monkeypatch.delenv(name, raising=False)


def test_healthy_report_keeps_workers_as_warnings(tmp_path):
    report = doctor.doctor_report(
        tmp_path,
        which_fn=healthy_which,
        run_fn=fake_runner,
        disk_usage_fn=healthy_disk,
    )

    assert report["status"] == "pass"
    assert report["exit_code"] == 0
    assert report["workers"]["melody"]["status"] == "not_installed"
    assert report["workers"]["muscriptor"]["status"] == "not_installed"
    assert report["failures"] == []


def test_missing_external_tools_fail_without_crashing(tmp_path, monkeypatch):
    monkeypatch.setattr(doctor, "_known_candidates", lambda _kind: [])

    def missing_which(name: str) -> str | None:
        return "C:/fake/git.exe" if name == "git" else None

    report = doctor.doctor_report(
        tmp_path,
        which_fn=missing_which,
        run_fn=fake_runner,
        disk_usage_fn=healthy_disk,
    )

    assert report["status"] == "fail"
    assert report["exit_code"] == 1
    assert {"ffmpeg", "ffprobe", "musescore"}.issubset(report["failures"])


def test_anaconda_python_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(doctor.sys, "executable", r"D:\Anaconda\python.exe")
    report = doctor.doctor_report(
        tmp_path,
        which_fn=healthy_which,
        run_fn=fake_runner,
        disk_usage_fn=healthy_disk,
    )

    assert report["checks"]["python"]["is_anaconda"] is True
    assert "python" in report["failures"]
    assert report["exit_code"] == 1


def test_low_disk_space_is_a_failure(tmp_path):
    def low_disk(_drive: str):
        return SimpleNamespace(total=100 * 1024**3, used=96 * 1024**3, free=4 * 1024**3)

    report = doctor.doctor_report(
        tmp_path,
        which_fn=healthy_which,
        run_fn=fake_runner,
        disk_usage_fn=low_disk,
    )

    assert report["checks"]["disk"]["status"] == "fail"
    assert report["exit_code"] == 1


def test_unicode_path_failure_is_reported(tmp_path):
    def unicode_failure(args, **kwargs):
        if len(args) > 1 and args[1] == "-c":
            return SimpleNamespace(
                returncode=0, stdout="A2VS_UNICODE_OK=False\n", stderr=""
            )
        return fake_runner(args, **kwargs)

    report = doctor.doctor_report(
        tmp_path,
        which_fn=healthy_which,
        run_fn=unicode_failure,
        disk_usage_fn=healthy_disk,
    )

    assert report["checks"]["unicode"]["status"] == "fail"
    assert "unicode" in report["failures"]


def test_json_output_and_exit_code(monkeypatch, capsys):
    fixture = {
        "schema_version": 1,
        "status": "pass",
        "exit_code": 0,
        "project_root": "D:/fixture",
        "checks": {},
        "nvidia": {"status": "not_found"},
        "workers": {},
        "failures": [],
        "warnings": [],
    }
    monkeypatch.setattr(cli, "doctor_report", lambda: fixture)

    assert cli.main(["doctor", "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["schema_version"] == 1
    assert output["status"] == "pass"

def create_melody_worker_files(tmp_path: Path):
    environment = tmp_path / "workers" / "melody" / ".venv"
    scripts = environment / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "python.exe").write_text("fake", encoding="utf-8")
    (tmp_path / "workers" / "melody" / "worker.py").write_text("fake", encoding="utf-8")


def test_installed_melody_worker_version_report_passes(tmp_path):
    create_melody_worker_files(tmp_path)

    def runner(args, **kwargs):
        if args[-2:] == ["--version", "--json"]:
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    {
                        "status": "pass",
                        "packages": {
                            "demucs": "4.1.0",
                            "basic_pitch": "0.4.0",
                            "torch": "2.1.2",
                            "onnxruntime": "1.20.0",
                        },
                        "device": "cpu",
                        "torch_cuda_available": False,
                        "onnxruntime_providers": ["CPUExecutionProvider"],
                        "model_cache": "cache/melody",
                        "torch_cache": "cache/torch",
                    }
                ),
                stderr="",
            )
        return fake_runner(args, **kwargs)

    report = doctor.doctor_report(
        tmp_path,
        which_fn=healthy_which,
        run_fn=runner,
        disk_usage_fn=healthy_disk,
    )

    assert report["status"] == "pass"
    assert report["workers"]["melody"]["status"] == "pass"
    assert report["workers"]["melody"]["versions"]["demucs"] == "4.1.0"
    assert not any(item["check"] == "worker:melody" for item in report["warnings"])


def test_installed_but_broken_melody_worker_is_warning(tmp_path):
    create_melody_worker_files(tmp_path)

    def runner(args, **kwargs):
        if args[-2:] == ["--version", "--json"]:
            return SimpleNamespace(returncode=1, stdout="", stderr="import failed")
        return fake_runner(args, **kwargs)

    report = doctor.doctor_report(
        tmp_path,
        which_fn=healthy_which,
        run_fn=runner,
        disk_usage_fn=healthy_disk,
    )

    assert report["status"] == "pass"
    assert report["exit_code"] == 0
    assert report["workers"]["melody"]["status"] == "broken"
    assert {"check": "worker:melody", "status": "broken", "reason": "version_command_failed"} in report["warnings"]