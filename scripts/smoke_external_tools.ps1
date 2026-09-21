param(
    [string]$Workspace = (Get-Location).Path
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $Workspace).Path
$tempRoot = Join-Path $root "temp\phase1a-external-tools"
New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Core Python executable not found: $python"
}

$doctorJson = & $python -m audio2violinscore.cli doctor --json | Out-String
if ($LASTEXITCODE -ne 0) {
    throw "doctor failed before external smoke test."
}
$doctor = $doctorJson | ConvertFrom-Json
$ffmpeg = $doctor.checks.ffmpeg.path
$ffprobe = $doctor.checks.ffprobe.path
$musescore = $doctor.checks.musescore.path
if ([string]::IsNullOrWhiteSpace($ffmpeg) -or [string]::IsNullOrWhiteSpace($ffprobe)) {
    throw "FFmpeg or ffprobe was not discovered by doctor."
}
if ([string]::IsNullOrWhiteSpace($musescore)) {
    throw "MuseScore was not discovered by doctor."
}

$wav = Join-Path $tempRoot "phase1a-tone.wav"
$toneScript = Join-Path $tempRoot "generate_tone.py"
@'
import math
import struct
import sys
import wave

path = sys.argv[1]
sample_rate = 16_000
frames = int(sample_rate * 0.25)
with wave.open(path, "wb") as stream:
    stream.setnchannels(1)
    stream.setsampwidth(2)
    stream.setframerate(sample_rate)
    samples = (int(0.25 * 32767 * math.sin(2 * math.pi * 440 * i / sample_rate)) for i in range(frames))
    stream.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))
'@ | Set-Content -LiteralPath $toneScript -Encoding UTF8
& $python $toneScript $wav
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $wav)) {
    throw "Synthetic WAV generation failed."
}

$probeOutput = & $ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $wav 2>&1
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($probeOutput -join ""))) {
    throw "ffprobe smoke test failed."
}
& $ffmpeg -hide_banner -loglevel error -i $wav -f null NUL
if ($LASTEXITCODE -ne 0) {
    throw "ffmpeg decode smoke test failed."
}

$musicXml = Join-Path $tempRoot "phase1a-fixture.musicxml"
$pdf = Join-Path $tempRoot "phase1a-fixture.pdf"
@'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Violin</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>D</step><octave>5</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>E</step><octave>5</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>F</step><octave>5</octave></pitch><duration>1</duration><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>
'@ | Set-Content -LiteralPath $musicXml -Encoding UTF8
$musescoreStdout = Join-Path $tempRoot "musescore-stdout.log"
$musescoreStderr = Join-Path $tempRoot "musescore-stderr.log"
$musescoreProcess = Start-Process -FilePath $musescore -ArgumentList @("-o", $pdf, $musicXml) -WorkingDirectory $root -Wait -PassThru -NoNewWindow -RedirectStandardOutput $musescoreStdout -RedirectStandardError $musescoreStderr
if ($musescoreProcess.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $pdf)) {
    throw "MuseScore MusicXML to PDF smoke test failed."
}
$pdfInfo = Get-Item -LiteralPath $pdf
if ($pdfInfo.Length -le 0) {
    throw "MuseScore produced a zero-byte PDF."
}

Write-Output "FFmpeg: $ffmpeg"
Write-Output "ffprobe: $ffprobe"
Write-Output "MuseScore: $musescore"
Write-Output "Synthetic WAV: $wav ($($probeOutput -join ' '))"
Write-Output "MusicXML/PDF: $musicXml -> $pdf ($($pdfInfo.Length) bytes)"
