# Audio2ViolinScore 环境审计

审计日期：2026-09-21
工作区：`D:\软件\扒谱`
审计阶段：Phase 0（已完成）
安装状态：未安装新依赖，未修改现有系统 Python；Git 初始化属于后续独立固化步骤

## 1. 审计结论

- 工作区中文路径可用：PowerShell、Python 文件访问、Python `subprocess` 均通过。
- D 盘剩余约 112.73 GB，高于施工方案要求的最低 12 GB。
- 已存在：uv、Git、Python 3.12.4、uv 管理的 Python 3.11.15、NVIDIA GPU 驱动工具。
- 未发现：FFmpeg、ffprobe、MuseScore 4。
- Python 3.10.20 显示为 uv 可下载版本，但当前未安装。
- 当前 `python` 指向 `D:\Anaconda\python.exe`，后续不得将项目依赖安装到该环境。
- Phase 0 审计开始时当前目录尚未初始化 Git；本次独立固化步骤随后执行 Git 初始化。

## 2. 系统与硬件

| 项目 | 实测结果 |
|---|---|
| Windows 注册表产品名 | `Windows 10 Home China` |
| Windows 显示版本 | `24H2` |
| Windows Build | `26100.7462`（CurrentBuild `26100`，UBR `7462`） |
| .NET 系统描述 | `Microsoft Windows 10.0.26100` |
| 系统架构 | `x64` |
| CPU | `AMD Ryzen 7 8845H w/ Radeon 780M Graphics` |
| CPU 逻辑处理器 | `16` |
| 物理核心数 | 本受限审计环境的 WMI 查询被拒绝，未作未经验证的推断 |
| 物理内存 | `23.29 GB`（约 24 GB） |
| 审计时可用内存 | `8.01 GB`（动态值） |
| NVIDIA GPU | `NVIDIA GeForce RTX 4060 Laptop GPU` |
| NVIDIA 驱动 | `581.80` |
| NVIDIA 显存 | `8188 MiB` |
| 审计时显存占用/利用率 | `1834 MiB` / `21%`（动态值） |

说明：用户环境描述为 Windows 11；本次本机原始字段同时报告了 `Windows 10 Home China` 和 Build `26100 / 24H2`，因此文档保留原始值，不把产品名字段擅自改写为“Windows 11”。Build/版本的最终产品归属应在后续需要时用系统“关于”页面复核。

## 3. 工具状态

| 工具 | 状态 | 实测信息 |
|---|---|---|
| `python` | 已存在 | Python `3.12.4`，`D:\Anaconda\python.exe` |
| `py --list` | 未发现 Python | 返回 `No installed Pythons found!`；这不影响 uv 管理的解释器 |
| uv | 已存在 | `uv 0.11.15`，`C:\Users\jxgm\.local\bin\uv.exe` |
| uv 管理 Python 3.11 | 已存在 | Python `3.11.15`，位于 `C:\Users\jxgm\AppData\Roaming\uv\python\...` |
| uv 管理 Python 3.10 | 未安装 | `3.10.20` 显示为 `<download available>` |
| Git | 已存在 | `git version 2.52.0.windows.1`，`C:\Program Files\Git\cmd\git.exe` |
| FFmpeg | 未发现 | `ffmpeg` 不在 PATH |
| ffprobe | 未发现 | `ffprobe` 不在 PATH |
| MuseScore 4 | 未发现 | `mscore`、`MuseScore4`、`MuseScore4.exe` 均不在 PATH；卸载注册表和常见安装目录也未发现 |
| GPU 工具 | 已存在 | `C:\Windows\System32\nvidia-smi.exe` 可正常返回 GPU 状态 |

Python 相关路径：

- 当前系统 Python 前缀：`D:\Anaconda`
- uv Python 目录：`C:\Users\jxgm\AppData\Roaming\uv\python`
- uv 缓存目录：`C:\Users\jxgm\AppData\Local\uv\cache`

`uv python list --only-installed` 的默认缓存初始化曾因受限环境对 uv 缓存目录的访问被拒绝；使用 `uv --no-cache python list --only-installed` 后确认已安装的 uv Python 为 3.11.15。该现象不代表 Python 3.11 不可用。

## 4. 磁盘与工作区

### D 盘

| 项目 | 实测值 |
|---|---:|
| 总容量 | 730.51 GB |
| 已用 | 617.78 GB |
| 可用 | 112.73 GB |
| 可用比例 | 15.43% |

结论：满足施工方案“开工前至少保留 12 GB”的门槛。每次下载模型或大型安装包前仍需重新检查剩余空间。

### 当前工作区

- Phase 0 审计开始时顶层只有 `Audio2ViolinScore_Codex施工方案.md`；随后创建了 `docs/ENVIRONMENT.md` 和 `.gitignore`。
- Phase 0 创建本文件及其父目录 `docs`。
- 当前工作区原始文件数量为 1，文件体积约为 0 GB（未计本次新增文档前）。
- Phase 0 审计本身未执行 `git init`；Git 初始化由后续固化步骤单独执行。

## 5. 中文路径兼容性

测试位置：`D:\软件\扒谱`；测试只使用现有方案文件，没有创建临时测试文件。

通过项目：

1. PowerShell `Test-Path -LiteralPath` 能正确识别工作区和方案文件。
2. Python 在该中文工作目录下启动，`os.getcwd()` 对应的工作目录存在。
3. Python 从命令行接收方案文件的完整 Unicode 路径，并确认文件存在。
4. Python 通过 `subprocess.run(..., cwd=os.getcwd())` 启动子 Python，返回码为 `0`。
5. 子进程在中文工作目录下确认相对路径方案文件存在。

判定：当前 Python/Windows subprocess 路径链路通过；后续 worker 调用必须继续使用参数数组和明确的 `cwd`，不得拼接未 quoting 的裸命令字符串。此次测试不替代 FFmpeg/MuseScore 安装后的实际 CLI smoke test。

## 6. Phase 1 精确安装计划

Phase 1 尚未开始，以下只作为下一阶段执行清单。

### 6.1 解释器与环境隔离

1. 不重装 uv；复用现有 `uv 0.11.15`。
2. 复用已存在的 uv Python `3.11.15` 创建：
   - `.venv-core`
   - `workers\muscriptor\.venv`
3. 仅在 Melody worker 安装前，用 uv 安装/获取 `Python 3.10.20`，创建 `workers\melody\.venv`。
4. 所有依赖只写入对应 `.venv`；禁止对 `D:\Anaconda` 执行全局 `pip install`。
5. 创建环境后立即记录解释器路径、Python 版本和 `uv.lock`，再进行下一环境。

### 6.2 Core 环境

在 `.venv-core` 中按施工方案建立最小 Core 依赖并锁定：`typer`、`rich`、`pydantic`、`mido`、按需使用的 `music21`、`numpy`、`pytest`、`ruff`。先完成 `uv run pytest`、`uv run ruff check .` 和最小 `a2vs doctor` 骨架验证。

### 6.3 Melody worker

在 Python 3.10 环境中安装并锁定施工方案基线：Demucs `4.1.x`、Basic Pitch `0.4.x`、ONNX Runtime 优先、`soundfile`；FFmpeg 作为外部可执行依赖，不复制进每个 worker。依次执行 import smoke test、10 秒测试音频分离、单声部 WAV 转 MIDI/JSON 和 Core subprocess 调用。

### 6.4 MuScriptor worker

在 Python 3.11 环境中安装当前稳定 MuScriptor `0.3.x` release，并单独记录代码许可与模型权重许可。先做 import，再下载模型权重，最后用 10 秒音频执行 CPU transcription 和 JSONL/MIDI 输出验证。

### 6.5 FFmpeg、MuseScore 与验证

1. 先再次探测 PATH，避免重复安装。
2. 若仍缺失，使用可信官方发行方式安装 FFmpeg，并验证 `ffmpeg -version` 与 `ffprobe -version`。
3. 安装 MuseScore Studio 4 本体，不安装 MuseSounds；记录实际 `MuseScore4.exe` 路径到项目配置。
4. 用最小 `MusicXML → PDF` smoke test 验证输出文件真实存在，不能只看进程返回码。
5. 安装/下载每个大型组件前重新检查 D 盘剩余空间。

### 6.6 预计新增磁盘占用

按施工方案预算，Phase 1 完成后的新增空间预计如下：

| 项目 | 预计新增 |
|---|---:|
| Core 环境 | < 0.5 GB |
| Melody worker（含 Python 3.10 与依赖） | 1–3 GB |
| MuScriptor worker | 2–4 GB |
| Demucs/Basic Pitch/MuScriptor 模型缓存 | 1–3 GB |
| MuseScore Studio 本体 | 约 0.5 GB |
| 下载缓存与短测试临时文件 | 2–4 GB |
| **总新增工作空间/缓存预算** | **约 7–15 GB** |

当前 D 盘可用 112.73 GB，按上限估算完成后仍约有 97.73 GB 可用，满足 12 GB 保留门槛。模型实际大小和依赖解析结果可能变化，安装后必须再做真实统计；不安装 CUDA、cuDNN、Docker、WSL、Anaconda 或 MuseSounds。

## 7. 本阶段未执行事项

- 未安装 FFmpeg、MuseScore、Python 3.10、Demucs、Basic Pitch、MuScriptor 或任何新依赖。
- 未修改 `D:\Anaconda` 或其他已有 Python 环境。
- Git 初始化不属于 Phase 0 环境审计，已由后续固化步骤单独执行。
- 未创建 Phase 1 的虚拟环境、项目目录或 lock 文件。
- 未运行需要真实音频、模型下载或 MusicXML 渲染的 smoke test。
