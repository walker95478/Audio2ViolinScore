# Architecture

## Phase 1A state

仓库当前只包含 Core 项目骨架、环境诊断和外部工具 smoke test。音频转录、后处理、路由和 backend worker 均未实现。

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

Core 使用仓库根目录的标准 `.venv`，而不是 `.venv-core`。Melody 和 MuScriptor 获授权后才会分别使用 `workers/<name>/.venv`。本阶段实际使用 `uv sync --no-editable`，因为中文路径下 editable `.pth` 会触发 Windows Python 的 GBK 解码问题；因此命令和文档直接调用 `.venv\Scripts` 入口。

FFmpeg/ffprobe 和 MuseScore 是外部运行时，不复制到 worker，也不写入 Python dependency lock。doctor 只读发现它们，顺序为显式环境变量 → PATH → 已知安装目录。

## Boundaries

- `src/audio2violinscore/doctor.py`: 环境发现、版本验证和结构化诊断。
- `src/audio2violinscore/cli.py`: 最小公开 CLI 入口。
- `scripts/`: 明确调用真实外部程序的 smoke test，不属于普通单元测试。
- `tests/`: mock/monkeypatch 单元测试，不依赖真实安装器或模型。
- `reports/benchmarks/`: 只允许小型、可审查的 benchmark metadata。
- `temp/`、`output/`、`.venv` 和 cache：运行时目录，禁止进入公开仓库。

## 后续边界

Phase 1B 才评估 Demucs、Basic Pitch、MuScriptor、模型权重及其独立环境；本阶段不创建 transcription、postprocess、router 或 AI backend 实现。
