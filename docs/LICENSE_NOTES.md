# License notes

本文件只记录 Phase 1A 实际引入或验证的组件，不构成未来商业使用的整体许可证清关。仓库当前没有新增商业歌曲、模型权重或 AI backend。

## Phase 1A components

| Component | Source/version | License/evidence |
|---|---|---|
| Python | uv-managed CPython 3.11.15 | 运行时解释器；发行版许可证应以 CPython 对应发行条款为准。未复制到仓库。 |
| pytest | 8.4.2，uv lock | PyPI 元数据为 MIT；仅用于测试开发依赖。 |
| Ruff | 0.16.8，uv lock | PyPI 元数据为 MIT；仅用于 lint 开发依赖。 |
| FFmpeg | winget `Gyan.FFmpeg`，tested `8.1.1` | winget 元数据报告 GPL-3.0；来源 `https://www.gyan.dev/ffmpeg/builds/`。它是外部运行时，不是 Python 精确锁定依赖。 |
| MuseScore Studio | winget `Musescore.Musescore`，`4.7.5.260831071`；CLI `4.7.5` | winget 元数据报告 GPL-3.0；来源 `https://musescore.org/en`。仅验证 CLI→PDF，不安装 MuseSounds。 |

FFmpeg 的旧施工方案 baseline `9.0.1` 没有在本阶段强制执行；实际保留并测试 `8.1.1`。未来若某个 backend 或 codec 提出更高版本要求，需要单独记录原因、兼容性和许可证影响后再升级。

## Not introduced

Demucs、Basic Pitch、MuScriptor、Beat This!、模型权重、CUDA/cuDNN、MuseSounds、版权音频和生成 benchmark 二进制均未在 Phase 1A 引入。它们的代码、模型和数据许可证必须在后续实际引入时逐项复核。
