"""Environment discovery and validation for the Phase 1A Core CLI."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

MIN_FREE_BYTES = 12 * 1024**3
REQUIRED_CHECKS = ("python", "git", "ffmpeg", "ffprobe", "musescore", "disk", "unicode")

RunFunction = Callable[..., Any]
WhichFunction = Callable[[str], str | None]
DiskUsageFunction = Callable[[str], Any]


def _find_project_root() -> Path:
    """Find the workspace root when the package is installed non-editably."""

    configured = os.environ.get("A2VS_PROJECT_ROOT")
    if configured:
        configured_path = Path(configured).expanduser()
        if configured_path.is_dir():
            return configured_path.resolve()

    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate

    source_path = Path(__file__).resolve()
    for candidate in (source_path.parent, *source_path.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate

    return current


PROJECT_ROOT = _find_project_root()


def _run_command(*args: Any, **kwargs: Any) -> Any:
    return subprocess.run(*args, **kwargs)


def _version_line(result: Any) -> str | None:
    output = "\n".join(
        value
        for value in (getattr(result, "stdout", ""), getattr(result, "stderr", ""))
        if value
    )
    for line in output.splitlines():
        if line.strip():
            return line.strip()[:240]
    return None


def _verify_executable(
    path: str,
    version_args: tuple[str, ...],
    run_fn: RunFunction,
    cwd: Path,
) -> dict[str, Any]:
    try:
        result = run_fn(
            [path, *version_args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except FileNotFoundError:
        return {"verified": False, "reason": "executable_not_found"}
    except subprocess.TimeoutExpired:
        return {"verified": False, "reason": "version_command_timeout"}
    except OSError:
        return {"verified": False, "reason": "version_command_os_error"}

    version = _version_line(result)
    return {
        "verified": result.returncode == 0,
        "returncode": result.returncode,
        "version": version,
        "reason": None if result.returncode == 0 else "version_command_failed",
    }


def _winget_candidates(
    package_prefix: str, executable_names: tuple[str, ...]
) -> list[Path]:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return []
    packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
    if not packages.is_dir():
        return []

    candidates: list[Path] = []
    for package_dir in sorted(packages.glob(f"{package_prefix}_*")):
        if not package_dir.is_dir():
            continue
        for executable_name in executable_names:
            candidates.extend(package_dir.rglob(executable_name))
    return candidates


def _known_candidates(kind: str) -> list[Path]:
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local_app_data = os.environ.get("LOCALAPPDATA")
    candidates: list[Path] = []

    if kind == "ffmpeg":
        candidates.extend(
            [
                Path(program_files) / "ffmpeg" / "bin" / "ffmpeg.exe",
                Path(r"C:\ffmpeg") / "bin" / "ffmpeg.exe",
            ]
        )
        candidates.extend(_winget_candidates("Gyan.FFmpeg", ("ffmpeg.exe",)))
    elif kind == "ffprobe":
        candidates.extend(
            [
                Path(program_files) / "ffmpeg" / "bin" / "ffprobe.exe",
                Path(r"C:\ffmpeg") / "bin" / "ffprobe.exe",
            ]
        )
        candidates.extend(_winget_candidates("Gyan.FFmpeg", ("ffprobe.exe",)))
    elif kind == "musescore":
        for base in (program_files, program_files_x86):
            candidates.extend(
                [
                    Path(base) / "MuseScore 4" / "bin" / "MuseScore4.exe",
                    Path(base) / "MuseScore Studio 4" / "bin" / "MuseScore4.exe",
                ]
            )
        if local_app_data:
            candidates.append(
                Path(local_app_data)
                / "Programs"
                / "MuseScore 4"
                / "bin"
                / "MuseScore4.exe"
            )
        candidates.extend(
            _winget_candidates("Musescore.Musescore", ("MuseScore4.exe",))
        )
    return candidates


def discover_tool(
    kind: str,
    *,
    env_names: tuple[str, ...],
    command_names: tuple[str, ...],
    which_fn: WhichFunction = shutil.which,
) -> dict[str, Any]:
    """Resolve a tool using explicit paths, PATH, then known installation paths."""

    for env_name in env_names:
        configured = os.environ.get(env_name)
        if configured:
            path = Path(configured.strip().strip('"'))
            if path.is_file():
                return {
                    "status": "found",
                    "path": str(path),
                    "source": f"env:{env_name}",
                }
            return {
                "status": "missing",
                "path": str(path),
                "source": f"env:{env_name}",
                "reason": "configured_path_not_found",
            }

    for command_name in command_names:
        found = which_fn(command_name)
        if found:
            return {"status": "found", "path": str(found), "source": "PATH"}

    for candidate in _known_candidates(kind):
        if candidate.is_file():
            return {"status": "found", "path": str(candidate), "source": "known_path"}

    return {"status": "missing", "path": None, "source": None, "reason": "not_found"}


def check_tool(
    kind: str,
    *,
    env_names: tuple[str, ...],
    command_names: tuple[str, ...],
    version_args: tuple[str, ...],
    cwd: Path,
    which_fn: WhichFunction,
    run_fn: RunFunction,
) -> dict[str, Any]:
    result = discover_tool(
        kind,
        env_names=env_names,
        command_names=command_names,
        which_fn=which_fn,
    )
    if result["status"] != "found":
        return result

    verification = _verify_executable(result["path"], version_args, run_fn, cwd)
    result.update(verification)
    result["status"] = "pass" if verification["verified"] else "fail"
    return result


def _is_anaconda_executable(executable: str) -> bool:
    normalized = executable.replace("/", "\\").lower()
    configured_root = os.environ.get("A2VS_ANACONDA_ROOT", r"D:\Anaconda")
    root = configured_root.replace("/", "\\").rstrip("\\").lower()
    return normalized == root or normalized.startswith(root + "\\")


def check_python() -> dict[str, Any]:
    executable = str(Path(sys.executable))
    major, minor, micro = sys.version_info[:3]
    is_anaconda = _is_anaconda_executable(executable)
    compatible = (major, minor) == (3, 11) and not is_anaconda
    return {
        "status": "pass" if compatible else "fail",
        "executable": executable,
        "version": f"{major}.{minor}.{micro}",
        "is_anaconda": is_anaconda,
        "required": "Python 3.11 and non-Anaconda executable",
    }


def check_disk(
    disk_usage_fn: DiskUsageFunction,
    drive: str = "D:\\",
) -> dict[str, Any]:
    try:
        usage = disk_usage_fn(drive)
    except OSError:
        return {"status": "fail", "drive": drive, "reason": "disk_usage_unavailable"}

    free_bytes = int(usage.free)
    return {
        "status": "pass" if free_bytes >= MIN_FREE_BYTES else "fail",
        "drive": drive,
        "free_bytes": free_bytes,
        "free_gb": round(free_bytes / 1024**3, 2),
        "minimum_free_gb": 12,
    }


def check_unicode_path(
    project_root: Path,
    run_fn: RunFunction,
) -> dict[str, Any]:
    root_text = str(project_root)
    roundtrip_ok = os.fsdecode(os.fsencode(root_text)) == root_text
    command = [
        sys.executable,
        "-c",
        "import os; print('A2VS_UNICODE_OK=' + str(os.path.isdir(os.getcwd())))",
    ]
    try:
        result = run_fn(
            command,
            cwd=root_text,
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        result = None

    subprocess_ok = bool(
        result
        and result.returncode == 0
        and "A2VS_UNICODE_OK=True" in (result.stdout or "")
    )
    return {
        "status": "pass" if roundtrip_ok and subprocess_ok else "fail",
        "cwd": root_text,
        "filesystem_roundtrip": roundtrip_ok,
        "subprocess_cwd": subprocess_ok,
    }


def check_nvidia(
    *,
    which_fn: WhichFunction,
    run_fn: RunFunction,
    cwd: Path,
) -> dict[str, Any]:
    executable = which_fn("nvidia-smi")
    if not executable:
        return {"status": "not_found", "path": None}
    args = [
        executable,
        "--query-gpu=name,driver_version,memory.total",
        "--format=csv,noheader",
    ]
    try:
        result = run_fn(
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "fail", "path": executable, "reason": "nvidia_smi_failed"}
    return {
        "status": "pass" if result.returncode == 0 else "fail",
        "path": executable,
        "summary": _version_line(result),
    }


def check_workers(project_root: Path) -> dict[str, Any]:
    workers: dict[str, Any] = {}
    for name in ("melody", "muscriptor"):
        environment = project_root / "workers" / name / ".venv"
        workers[name] = {
            "status": "installed" if environment.is_dir() else "not_installed",
            "path": str(environment),
        }
    return workers


def doctor_report(
    project_root: Path | None = None,
    *,
    which_fn: WhichFunction = shutil.which,
    run_fn: RunFunction = _run_command,
    disk_usage_fn: DiskUsageFunction = shutil.disk_usage,
) -> dict[str, Any]:
    root = Path(project_root or _find_project_root()).resolve()
    checks = {
        "python": check_python(),
        "git": check_tool(
            "git",
            env_names=(),
            command_names=("git",),
            version_args=("--version",),
            cwd=root,
            which_fn=which_fn,
            run_fn=run_fn,
        ),
        "ffmpeg": check_tool(
            "ffmpeg",
            env_names=("A2VS_FFMPEG_PATH", "FFMPEG_PATH"),
            command_names=("ffmpeg", "ffmpeg.exe"),
            version_args=("-version",),
            cwd=root,
            which_fn=which_fn,
            run_fn=run_fn,
        ),
        "ffprobe": check_tool(
            "ffprobe",
            env_names=("A2VS_FFPROBE_PATH", "FFPROBE_PATH"),
            command_names=("ffprobe", "ffprobe.exe"),
            version_args=("-version",),
            cwd=root,
            which_fn=which_fn,
            run_fn=run_fn,
        ),
        "musescore": check_tool(
            "musescore",
            env_names=("A2VS_MUSESCORE_PATH", "MUSESCORE_PATH"),
            command_names=("MuseScore4.exe", "mscore", "mscore4"),
            version_args=("--version",),
            cwd=root,
            which_fn=which_fn,
            run_fn=run_fn,
        ),
        "disk": check_disk(disk_usage_fn),
        "unicode": check_unicode_path(root, run_fn),
    }
    workers = check_workers(root)
    nvidia = check_nvidia(which_fn=which_fn, run_fn=run_fn, cwd=root)
    failures = [name for name in REQUIRED_CHECKS if checks[name]["status"] != "pass"]
    warnings = []
    if nvidia["status"] != "pass":
        warnings.append({"check": "nvidia", "status": nvidia["status"]})
    for name, result in workers.items():
        if result["status"] == "not_installed":
            warnings.append({"check": f"worker:{name}", "status": "not_installed"})

    return {
        "schema_version": 1,
        "status": "pass" if not failures else "fail",
        "exit_code": 0 if not failures else 1,
        "project_root": str(root),
        "checks": checks,
        "nvidia": nvidia,
        "workers": workers,
        "failures": failures,
        "warnings": warnings,
    }


def format_human(report: dict[str, Any]) -> str:
    lines = [
        f"Audio2ViolinScore doctor: {report['status'].upper()}",
        f"Project: {report['project_root']}",
    ]
    for name, result in report["checks"].items():
        status = result.get("status", "unknown").upper()
        details = (
            result.get("version") or result.get("path") or result.get("reason") or ""
        )
        lines.append(f"- {name}: {status}" + (f" ({details})" if details else ""))
    nvidia = report["nvidia"]
    lines.append(
        f"- nvidia: {nvidia['status'].upper()}"
        + (f" ({nvidia.get('summary')})" if nvidia.get("summary") else "")
    )
    for name, result in report["workers"].items():
        lines.append(f"- worker:{name}: {result['status'].upper()}")
    if report["failures"]:
        lines.append("Failures: " + ", ".join(report["failures"]))
    if report["warnings"]:
        lines.append(
            "Warnings: " + ", ".join(item["check"] for item in report["warnings"])
        )
    lines.append(f"Exit code: {report['exit_code']}")
    return "\n".join(lines)
