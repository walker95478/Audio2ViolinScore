# Audio2ViolinScore 环境审计与 Phase 1A 基线

审计日期：2026-09-21
工作区：`D:\软件\扒谱`
阶段：Phase 0 已审计并固化；Phase 1A 已完成并已推送

## 1. 当前结论

- Core 标准环境已创建为 `D:\软件\扒谱\.venv`，使用 uv 管理的 CPython 3.11.15；没有使用 `D:\Anaconda\python.exe`。
- Core 只安装当前实际使用的开发依赖：pytest 8.4.2、Ruff 0.16.8；运行时 doctor 只使用 Python 标准库。
- FFmpeg/ffprobe 保留并验证现有 8.1.1，未升级到施工方案旧 baseline 9.0.1。FFmpeg 是外部运行时依赖，不作为 Python 依赖精确锁定。
- MuseScore Studio 4 已通过 winget 用户范围命令安装并验证：winget 版本 4.7.5.260831071，CLI 报告 4.7.5。
- `a2vs doctor --json` 返回 `status=pass`、退出码 `0`；两个未来 worker 未安装只产生 warning。
- FFmpeg/ffprobe WAV probe/decode 和 MuseScore MusicXML→PDF smoke test 均通过。生成物只保留在被 Git 忽略的 `temp/`。
- 本阶段没有安装 Demucs、Basic Pitch、MuScriptor、模型权重、CUDA/cuDNN 或 MuseSounds。

## 2. 系统与硬件（Phase 0 原始审计）

| 项目 | 实测结果 |
|---|---|
| Windows 注册表产品名 | `Windows 10 Home China` |
| Windows 显示版本 | `24H2` |
| Windows Build | `26100.7462`（CurrentBuild `26100`，UBR `7462`） |
| 系统架构 | `x64` |
| CPU | `AMD Ryzen 7 8845H w/ Radeon 780M Graphics` |
| CPU 逻辑处理器 | `16` |
| 物理内存 | `23.29 GB`（约 24 GB） |
| NVIDIA GPU | `NVIDIA GeForce RTX 4060 Laptop GPU` |
| NVIDIA 驱动 | `581.80` |
| NVIDIA 显存 | `8188 MiB` |

用户环境描述为 Windows 11；本机原始系统字段仍报告 `Windows 10 Home China` 和 Build `26100 / 24H2`，因此这里保留原始值，不擅自改写产品名字段。

## 3. Phase 1A 工具状态

| 工具 | 实际状态 | 路径/版本 |
|---|---|---|
| Core Python | PASS | `D:\软件\扒谱\.venv\Scripts\python.exe`，Python `3.11.15` |
| uv | PASS | `uv 0.11.15` |
| Git | PASS | `C:\Program Files\Git\cmd\git.EXE`，`git version 2.52.0.windows.1` |
| FFmpeg | PASS | `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.EXE` |
| ffprobe | PASS | 同一 FFmpeg 8.1.1 `bin` 目录下的 `ffprobe.EXE` |
| MuseScore Studio 4 | PASS | `C:\Program Files\MuseScore 4\bin\MuseScore4.exe`；winget `4.7.5.260831071`，CLI `4.7.5` |
| D: 空间 | PASS | 实测可用 `112.43 GiB`，门槛 `12 GiB` |
| 中文路径 subprocess | PASS | 文件系统 round-trip 和中文 cwd 子进程均通过 |
| NVIDIA 可见性 | PASS | RTX 4060 Laptop GPU，驱动 `581.80`，显存 `8188 MiB` |
| `workers/melody` | warning | `.venv` 未安装；属于后续阶段 |
| `workers/muscriptor` | warning | `.venv` 未安装；属于后续阶段 |

### 外部运行时版本政策

FFmpeg 当前 tested version 为 `8.1.1`。它由系统/winget 提供，是外部运行时可执行依赖，不写入 `pyproject.toml` 的 Python dependencies，也不要求 `uv.lock` 锁定其精确版本。施工方案中的 `9.0.1` 仅作为旧 baseline 保留在历史记录中，不是当前硬性要求。若后续 Demucs、Basic Pitch、MuScriptor 或具体 codec 明确要求更高版本，再单独评估升级。

MuseScore 同样由 doctor 在显式环境变量、PATH、已知安装目录的顺序下只读发现；程序不自动修复 PATH 或改写系统配置。此次安装命令显式使用了 `--scope user` 和固定版本，安装器实际注册的目录为 `C:\Program Files\MuseScore 4`；没有另行改用系统范围命令。

## 4. Core 环境与隔离

Core 环境入口：

```text
D:\软件\扒谱\.venv\Scripts\python.exe
D:\软件\扒谱\.venv\Scripts\a2vs.exe
```

已解析的直接开发依赖：

| 包 | 版本 | 用途 |
|---|---:|---|
| pytest | 8.4.2 | 单元测试 |
| ruff | 0.16.8 | lint |

项目没有把依赖安装到 `D:\Anaconda`。由于 Windows Python 在中文工作区中读取 editable 安装产生的 `.pth` 时出现 GBK 解码错误，本阶段最终采用非 editable 安装；这不会改变系统 Python，也不会把源目录写入 site-packages 的 `.pth`。

推荐命令：

```powershell
$env:UV_CACHE_DIR = "D:\软件\扒谱\cache\uv"
uv sync --no-editable --python 3.11.15 --no-python-downloads
.\.venv\Scripts\a2vs.exe doctor
.\.venv\Scripts\a2vs.exe doctor --json
.\.venv\Scripts\pytest.exe
.\.venv\Scripts\ruff.exe check .
```

## 5. doctor 验收

支持的命令：

```text
a2vs doctor
a2vs doctor --json
```

实际 JSON 验收结果：

- `status`: `pass`
- `exit_code`: `0`
- required checks：Python、Git、FFmpeg、ffprobe、MuseScore、D 盘空间、中文路径全部 `pass`
- warning：`worker:melody`、`worker:muscriptor` 为 `not_installed`
- NVIDIA 为 `pass`，但不是必需检查
- 参数/配置错误退出码为 `2`；必需检查失败退出码为 `1`

工具发现顺序固定为：显式环境变量（`A2VS_FFMPEG_PATH`、`A2VS_FFPROBE_PATH`、`A2VS_MUSESCORE_PATH` 等）→ PATH → 已知 winget/安装目录。

## 6. 中文路径兼容性与 workaround

工作区 `D:\软件\扒谱` 的普通 Python 文件访问、`subprocess` 中文 cwd、FFmpeg/ffprobe 和 MuseScore 实际 CLI 均已验证通过。

首次使用默认 editable `uv sync` 时，`.venv\Lib\site-packages` 生成了指向中文源目录的 editable `.pth`；Windows Python 3.11 site 初始化按 GBK 读取该文件，出现 `UnicodeDecodeError`。在得到明确许可后，只删除并重建了项目自己的 `D:\软件\扒谱\.venv`，随后使用：

```powershell
uv sync --no-editable --python 3.11.15 --no-python-downloads
```

最终 `.venv` 不含该 editable `.pth`，直接调用 `.venv\Scripts` 入口和 `python -m audio2violinscore.cli` 均正常。该 workaround 已记录在 README、架构文档和本文件中。

## 7. Git 与安全边界

- Phase 1A 只提交源码、测试、配置模板、文档、smoke 脚本和 `uv.lock`。
- `.venv`、uv cache、`temp/`、`output/`、音频、模型权重、生成 PDF/MIDI、日志和密钥均由 `.gitignore` 排除。
- 当前没有提交商业歌曲、模型权重、虚拟环境或 smoke test 二进制产物。
- Phase 1B 已完成本地实现与合成链路验收；MuScriptor、后处理、正式 MusicXML 和 benchmark 决策仍暂停。
## 8. Phase 1B Melody Worker 实测状态

本阶段完成了 Core Worker Protocol v1、Canonical Note Events v1、独立 Melody Worker 和 Core subprocess client。Core .venv 没有重装或新增包；当前源码验收使用现有 Core Python 配合 PYTHONPATH=src，避免违反 Core 环境隔离要求。

### 8.1 隔离环境与版本

| 项目 | 实测结果 |
|---|---|
| Worker Python | workers/melody/.venv/Scripts/python.exe，CPython 3.10.20 |
| Demucs | 4.1.0 |
| Basic Pitch | 0.4.0 |
| PyTorch | 2.1.2+cpu，CPU wheel source |
| ONNX Runtime | 1.23.2 |
| soundfile | 0.14.0 |
| setuptools | 80.10.2；为 resampy 的 pkg_resources 运行时引用提供兼容性 |
| Worker device | cpu |
| torch.cuda.is_available() | false |
| ONNX providers | AzureExecutionProvider、CPUExecutionProvider；未安装 CUDA/cuDNN provider |
| TensorFlow | 未安装 |
| 模型 | htdemucs，只在合成 smoke 中下载/使用；不提交权重 |

Worker 版本检查：

    workers\melody\.venv\Scripts\python.exe workers\melody\worker.py --version --json

Core doctor 通过源码入口执行时会调用同一个 worker 版本命令，并报告 Python、worker 路径、包版本、CPU device 和缓存逻辑路径：

    $env:PYTHONPATH = "$PWD\src"
    .\.venv\Scripts\python.exe -m audio2violinscore.cli doctor --json

本机 NVIDIA/GPU 探测逻辑仍保留。当前普通用户执行 nvidia-smi 返回权限不足，因此 doctor 将它记录为非必需 warning；这不改变 Phase 0 记录的 RTX 4060 Laptop GPU，也不触发 CUDA 安装。

### 8.2 缓存与运行边界

Worker 在导入 Demucs/Basic Pitch 前设置：

- TORCH_HOME → cache/torch
- A2VS_MODEL_CACHE → cache/melody
- HF_HOME → cache/melody/huggingface
- HF_HUB_CACHE / HUGGINGFACE_HUB_CACHE → cache/melody/huggingface/hub
- NUMBA_CACHE_DIR → cache/melody/numba

所有路径均是相对于项目根目录的逻辑缓存位置；cache/、temp/、output/ 和两个 .venv 都被 Git 忽略。第一次诊断性运行在 Worker 修正缓存变量前可能在 %USERPROFILE%\.cache\huggingface 留下了未跟踪模型缓存；该用户缓存没有被删除，后续 Worker 已固定使用项目 D 盘缓存。

### 8.3 合成端到端验收

scripts/smoke_melody_worker.ps1 生成本地短 WAV，经 Core melody_client 启动 worker，完成：

1. Demucs htdemucs CPU separation；
2. stems/vocals.wav；
3. Basic Pitch 0.4.0 ONNX inference；
4. raw/basic_pitch.mid；
5. canonical/notes.json。

最近一次脚本验收成功：status success，Canonical Note Events 16 条，WAV、MIDI、Canonical JSON 均为非零字节，并通过 MIDI 音高 0..127、onset_sec >= 0、offset_sec > onset_sec 校验。

samples/input/prom_dress-mxmtoon-prom_dress.mp3 当前不存在，因此 prom dress smoke 保持 pending；不下载、不联网寻找替代商业歌曲，也不执行该 smoke。

### 8.4 本阶段边界

本阶段没有安装 MuScriptor、TensorFlow、CUDA/cuDNN 或 MuseSounds；没有创建后处理、自动路由、正式 MusicXML 或 benchmark 结论。reports/benchmarks/README.md 只定义未来允许提交的轻量 JSON/Markdown metadata。