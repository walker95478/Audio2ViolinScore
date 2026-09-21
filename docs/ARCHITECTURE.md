# Architecture

## Phase 1A state

The repository currently contains only the Core orchestration layer and environment diagnostics. Transcription, post-processing, routing, and backend workers are intentionally not implemented.

```text
Core CLI / doctor
        |
        | future subprocess + structured protocol
        +--------------------+
        |                    |
        v                    v
Melody worker          MuScriptor worker
  (future)                (future)
```

The Core environment is the repository `.venv`. Melody and MuScriptor will use independent `workers/<name>/.venv` environments when those phases are authorized. External FFmpeg/ffprobe and MuseScore are discovered as read-only executables; they are not copied into workers.

## Boundaries

- `src/audio2violinscore/doctor.py`: environment discovery and structured diagnostics.
- `src/audio2violinscore/cli.py`: the minimal public CLI entry point.
- `scripts/`: explicit smoke tests that may invoke real external tools.
- `reports/benchmarks/`: only small, reviewable benchmark metadata.
