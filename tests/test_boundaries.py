from __future__ import annotations

from pathlib import Path

BACKEND_NAMES = ("demucs", "basic_pitch", "torch", "tensorflow", "muscriptor")


def test_core_source_does_not_import_backend_packages():
    source_root = Path(__file__).parents[1] / "src" / "audio2violinscore"
    source = "\n".join(path.read_text(encoding="utf-8") for path in source_root.rglob("*.py"))

    for name in BACKEND_NAMES:
        assert f"import {name}" not in source
        assert f"from {name}" not in source


def test_melody_worker_does_not_import_core_package():
    worker_path = Path(__file__).parents[1] / "workers" / "melody" / "worker.py"
    source = worker_path.read_text(encoding="utf-8")

    assert "audio2violinscore" not in source