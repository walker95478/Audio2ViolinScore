# License notes

This file records licenses from components actually introduced or installed in Phase 1A. It is not a blanket clearance for future commercial use.

## Phase 1A components

| Component | Source/version | License/evidence |
|---|---|---|
| Python | uv-managed CPython 3.11.15 | Record the interpreter distribution metadata during Phase 1A verification. |
| pytest | uv lock | Record package metadata from the resolved environment. |
| Ruff | uv lock | Record package metadata from the resolved environment. |
| FFmpeg | winget `Gyan.FFmpeg` | Winget metadata reports GPL-3.0; source is `https://www.gyan.dev/ffmpeg/builds/`. |
| MuseScore Studio | winget `Musescore.Musescore` | Winget metadata reports GPL-3.0; source is `https://musescore.org/en`. |

Future AI backends, model weights, Demucs, Basic Pitch, MuScriptor, Beat This!, and any downloaded models remain **pending verification** until their exact versions and license texts are actually introduced.
