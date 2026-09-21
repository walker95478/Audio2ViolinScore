# Disk usage

This file is generated at the end of Phase 1A. It must report measured sizes rather than only estimates.

Required scopes:

- project directory, excluding `.git` as a separate metadata row;
- `.venv`;
- `tools/` if present;
- MuseScore installation directory if reliably discoverable;
- uv cache;
- `temp/`;
- `output/`;
- D: total, used, free, and free percentage.

Runtime directories are intentionally ignored by Git. No audio, model, PDF, or MIDI artifacts belong in this report's tracked content.
