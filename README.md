# Audio2ViolinScore

Audio2ViolinScore 是一个本地运行的“音频 → 小提琴主旋律乐谱”项目。

当前 Phase 1A 已实现：

- Core Python 3.11 项目骨架；
- `a2vs doctor` 环境诊断命令；
- FFmpeg/ffprobe 与 MuseScore Studio 4 的外部工具发现接口；
- 基础单元测试与外部工具 smoke test 脚本。

当前尚未实现音频转录、后处理或自动 backend 路由，也不会在本阶段安装 Demucs、Basic Pitch、MuScriptor 或模型权重。

## Core 环境

项目使用 uv 管理标准 `.venv`，要求 Python 3.11。禁止把依赖安装到已有的 `D:\Anaconda` 环境。

```powershell
uv sync
uv run a2vs doctor
uv run a2vs doctor --json
uv run pytest
uv run ruff check .
```

## 外部工具

FFmpeg、ffprobe 和 MuseScore 路径由 doctor 按以下顺序发现：显式环境变量、PATH、已知 winget 安装目录。可用 `.env.example` 中的变量名显式设置路径，但程序不会自动修改系统配置。

真实外部程序验证使用：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_external_tools.ps1
```

## 项目边界

版权音频、模型权重、缓存、虚拟环境和生成结果只保留在本地运行目录，不提交到公开仓库。长期追踪的 benchmark 轻量结果只能放在 `reports/benchmarks/<case>/`，并且只允许 JSON、Markdown 和小型文本 metadata。
