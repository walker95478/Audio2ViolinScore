# Audio2ViolinScore

Audio2ViolinScore 是一个本地运行的“音频 → 小提琴主旋律乐谱”项目。

当前 Phase 1A 已实现：

- Core Python 3.11 项目骨架；
- `a2vs doctor` 与 `a2vs doctor --json` 环境诊断命令；
- FFmpeg/ffprobe 与 MuseScore Studio 4 的外部工具发现接口；
- 基础单元测试与独立外部工具 smoke test 脚本；
- Core 环境、许可证边界和磁盘实测文档。

当前尚未实现音频转录、后处理或自动 backend 路由，也不会在本阶段安装 Demucs、Basic Pitch、MuScriptor、模型权重、CUDA/cuDNN 或 MuseSounds。

## Core 环境

项目使用 uv 管理标准 `.venv`，要求 Python 3.11。禁止把依赖安装到已有的 `D:\Anaconda` 环境。由于 Windows Python 在中文路径下读取 editable `.pth` 可能按 GBK 解码失败，本项目使用 `--no-editable` 安装，并直接调用 `.venv\Scripts` 入口。

```powershell
$env:UV_CACHE_DIR = "D:\软件\扒谱\cache\uv"
uv sync --no-editable --python 3.11.15 --no-python-downloads
.\.venv\Scripts\a2vs.exe doctor
.\.venv\Scripts\a2vs.exe doctor --json
.\.venv\Scripts\pytest.exe
.\.venv\Scripts\ruff.exe check .
```

如果要明确使用已安装的 3.11.15 解释器，可将 `--python` 替换为本机 uv Python 的完整路径；不要使用 `D:\Anaconda\python.exe`。

## 外部工具基线

- FFmpeg/ffprobe：tested version `8.1.1`，保留现状，不升级旧方案中的 `9.0.1`。它是外部运行时依赖，不是 `pyproject.toml` 或 `uv.lock` 中的 Python 精确依赖。
- MuseScore Studio 4：winget `4.7.5.260831071`，CLI `4.7.5`。
- doctor 按“显式环境变量 → PATH → 已知安装目录”发现工具，不自动修复或修改系统配置。

真实外部程序验证使用：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_external_tools.ps1
```

脚本会生成短 WAV 和最小 MusicXML 到被忽略的 `temp\phase1a-external-tools`，验证 ffprobe probe、FFmpeg decode 以及 MuseScore MusicXML→PDF 且检查 PDF 非零字节。正常单元测试不依赖这些外部程序。

## 中文路径 workaround

首次默认 editable `uv sync` 可能在 `.venv\Lib\site-packages` 写入指向中文源目录的 `.pth`，Windows Python 3.11 site 初始化会按 GBK 读取并报 `UnicodeDecodeError`。当前项目使用：

```powershell
uv sync --no-editable --python 3.11.15 --no-python-downloads
```

只需直接调用 `.venv\Scripts` 下的程序即可。该 workaround 已通过 `a2vs doctor`、pytest、Ruff 和真实 FFmpeg/MuseScore smoke test 验证。

## 项目边界

版权音频、模型权重、缓存、虚拟环境和生成结果只保留在本地运行目录，不提交到公开仓库。长期追踪的 benchmark 轻量结果只能放在 `reports/benchmarks/<case>/`，并且只允许 JSON、Markdown 和小型文本 metadata。

Phase 1A 完成后暂停，等待审查；Phase 1B 才会另行评估 transcription backend、模型和 worker 环境。
