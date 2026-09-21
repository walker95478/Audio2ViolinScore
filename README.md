# Audio2ViolinScore

Audio2ViolinScore 是一个本地运行的“音频 → 小提琴主旋律乐谱”项目。

当前 Phase 1B 已实现：

- Core Python 3.11 项目骨架和 a2vs doctor 源码；
- Worker Protocol v1 与 Canonical Note Events v1；
- 独立 workers/melody/.venv（Python 3.10.20、CPU-only PyTorch、Demucs、Basic Pitch、ONNX Runtime）；
- Core melody_client subprocess boundary；
- 合成音频端到端：Demucs vocals → Basic Pitch → raw MIDI + Canonical JSON；
- 版本、GPU 可见性、缓存和磁盘审计文档。

本阶段仍未实现 MuScriptor、后处理、自动路由、正式 MusicXML 或 benchmark 决策；不安装 CUDA/cuDNN，不下载 MuseSounds。

## Core 环境

项目使用 uv 管理标准 .venv，要求 Python 3.11。禁止把依赖安装到已有的 D:\Anaconda 环境。由于 Windows Python 在中文路径下读取 editable .pth 可能按 GBK 解码失败，本项目使用 --no-editable 安装，并直接调用 .venv\Scripts 入口。

本阶段按用户要求没有重装 Core .venv。验证当前工作区源码时：

    $env:PYTHONPATH = "$PWD\src"
    .\.venv\Scripts\python.exe -m audio2violinscore.cli doctor
    .\.venv\Scripts\python.exe -m audio2violinscore.cli doctor --json
    .\.venv\Scripts\pytest.exe
    .\.venv\Scripts\ruff.exe check .

## Melody Worker

Worker 使用独立环境和锁文件：

    workers\melody\.venv\Scripts\python.exe workers\melody\worker.py --version --json
    .\scripts\smoke_melody_worker.ps1

实际固定版本：

- Python 3.10.20
- Demucs 4.1.0
- Basic Pitch 0.4.0
- PyTorch 2.1.2+cpu
- ONNX Runtime 1.23.2
- soundfile 0.14.0

运行时缓存统一到项目 cache\melody / cache\torch，不进入 Git。Worker 只接受 htdemucs、vocals、cpu 这组 Phase 1B options。

## 外部工具基线

- FFmpeg/ffprobe：tested version 8.1.1，保留现状，不升级旧方案中的 9.0.1。它是外部运行时依赖，不是 pyproject.toml 或 uv.lock 中的 Python 精确依赖。
- MuseScore Studio 4：winget 4.7.5.260831071，CLI 4.7.5。
- doctor 按“显式环境变量 → PATH → 已知安装目录”发现工具，不自动修复或修改系统配置。
- doctor 保留 NVIDIA/GPU 探测，但不会安装 CUDA/cuDNN。

## Smoke 与版权边界

真实 backend smoke 只使用脚本生成的短 WAV。当前没有 samples\input\prom_dress-mxmtoon-prom_dress.mp3，因此 prom dress smoke 为 pending；不下载、不联网寻找替代音频。音频、stems、模型、缓存、temp/output 和生成 PDF/MIDI 均不提交公开仓库。

普通测试：

    $env:PYTHONPATH = "$PWD\src"
    .\.venv\Scripts\pytest.exe
    .\.venv\Scripts\ruff.exe check .
    workers\melody\.venv\Scripts\python.exe -m pytest workers\melody\tests

外部 smoke 与普通单元测试分离；模型和生成文件只保留在被忽略目录。