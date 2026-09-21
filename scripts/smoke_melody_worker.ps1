[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$corePython = Join-Path $root ".venv\Scripts\python.exe"
$tempRoot = Join-Path $root "temp\phase1b-melody"
$audioPath = Join-Path $tempRoot "synthetic_440hz.wav"
$invokePath = Join-Path $tempRoot "invoke_client.py"

if (-not (Test-Path -LiteralPath $corePython -PathType Leaf)) {
    throw "Core Python not found: $corePython"
}
New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null

function Write-Utf8File([string]$Path, [string]$Content) {
    [IO.File]::WriteAllText($Path, $Content, [Text.UTF8Encoding]::new($false))
}

$generator = @"
from __future__ import annotations

import math
import struct
import sys
import wave
from pathlib import Path

output = Path(sys.argv[1])
sample_rate = 44100
segments = [
    (0.35, None),
    (1.15, 440.0),
    (0.25, None),
    (1.15, 523.25),
    (0.25, None),
    (0.95, 440.0),
]
frames: list[tuple[int, int]] = []
for duration, frequency in segments:
    count = round(duration * sample_rate)
    for index in range(count):
        if frequency is None:
            value = 0.0
        else:
            time_sec = index / sample_rate
            attack = min(1.0, time_sec / 0.025)
            release = min(1.0, (duration - time_sec) / 0.035)
            envelope = max(0.0, min(attack, release))
            value = envelope * (
                0.62 * math.sin(2.0 * math.pi * frequency * time_sec)
                + 0.22 * math.sin(2.0 * math.pi * frequency * 2.0 * time_sec)
                + 0.11 * math.sin(2.0 * math.pi * frequency * 3.0 * time_sec)
            )
        sample = max(-32767, min(32767, round(value * 18000)))
        frames.append((sample, sample))
output.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(output), "wb") as handle:
    handle.setnchannels(2)
    handle.setsampwidth(2)
    handle.setframerate(sample_rate)
    handle.writeframes(b"".join(struct.pack("<hh", left, right) for left, right in frames))
print(output)
"@
Write-Utf8File $((Join-Path $tempRoot "generate_synthetic.py")) $generator
& $corePython (Join-Path $tempRoot "generate_synthetic.py") $audioPath
if ($LASTEXITCODE -ne 0) { throw "synthetic audio generation failed" }

$invoker = @"
from __future__ import annotations

import json
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
audio_path = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(root / "src"))

from audio2violinscore.workers.melody_client import MelodyClient

client = MelodyClient(root, timeout_seconds=1800)
output_root = client.output_root
before = {path.name for path in output_root.iterdir() if path.is_dir()} if output_root.is_dir() else set()
result = client.run(audio_path)
if result.status != "success":
    raise RuntimeError(f"expected success, got {result.status}")
new_outputs = [
    path for path in output_root.iterdir()
    if path.is_dir() and path.name not in before
]
if not new_outputs:
    raise RuntimeError("could not identify the new worker output directory")
output_dir = max(new_outputs, key=lambda path: path.stat().st_mtime_ns)
required = ["vocals_stem", "raw_midi", "canonical_notes"]
for key in required:
    artifact = result.artifacts.get(key)
    if not isinstance(artifact, dict) or not artifact.get("path"):
        raise RuntimeError(f"missing artifact: {key}")
    path = output_dir / artifact["path"]
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"empty artifact: {key}: {path}")
canonical_path = output_dir / result.artifacts["canonical_notes"]["path"]
document = json.loads(canonical_path.read_text(encoding="utf-8"))
if document.get("schema_version") != 1:
    raise RuntimeError("canonical schema version mismatch")
notes = document.get("notes")
if not isinstance(notes, list) or not notes:
    raise RuntimeError("synthetic audio produced no canonical notes")
for note in notes:
    if not 0 <= int(note["pitch_midi"]) <= 127:
        raise RuntimeError("canonical pitch outside MIDI range")
    if float(note["onset_sec"]) < 0 or float(note["offset_sec"]) <= float(note["onset_sec"]):
        raise RuntimeError("canonical timing invariant failed")
print(json.dumps({
    "status": result.status,
    "note_count": len(notes),
    "artifacts": {key: result.artifacts[key]["path"] for key in required},
}, ensure_ascii=False, indent=2))
"@
Write-Utf8File $invokePath $invoker
& $corePython $invokePath $root $audioPath
if ($LASTEXITCODE -ne 0) { throw "Core to Melody Worker synthetic smoke failed" }

$commercial = Join-Path $root "samples\input\prom_dress-mxmtoon-prom_dress.mp3"
if (Test-Path -LiteralPath $commercial -PathType Leaf) {
    Write-Output "prom dress smoke: pending (input now exists; not executed by this script)"
} else {
    Write-Output "prom dress smoke: pending (samples\input\prom_dress-mxmtoon-prom_dress.mp3 not found)"
}