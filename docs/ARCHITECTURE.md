# Architecture

## Phase 1B state

当前仓库包含 Core 骨架、环境诊断、外部工具 smoke test、Worker Protocol v1、Canonical Note Events v1、独立 Melody Worker 和 Core subprocess client。端到端只覆盖合成音频；MuScriptor、后处理、自动路由、正式 MusicXML 和 benchmark 决策仍未实现。

    Core CLI / doctor
            |
            | UTF-8 request.json / result.json
            v
    MelodyClient (Core .venv, stdlib boundary)
            |
            | subprocess, shell=False, timeout, captured logs
            v
    workers/melody/.venv (Python 3.10.20, CPU packages)
            |
            +--> Demucs 4.1.0 / htdemucs / CPU
            |       |
            |       +--> stems/vocals.wav
            |
            +--> Basic Pitch 0.4.0 / ONNX Runtime
                    |
                    +--> raw/basic_pitch.mid
                    +--> canonical/notes.json

Core 不 import demucs、basic_pitch、torch、tensorflow 或 muscriptor。Worker 不 import audio2violinscore；两者只通过 UTF-8 JSON 文件协议和 subprocess 返回码通信。

## Worker Protocol v1

请求固定包含：

    {
      "schema_version": 1,
      "request_id": "uuid",
      "operation": "transcribe",
      "input": {"audio_path": "absolute path"},
      "options": {
        "model": "htdemucs",
        "target_stem": "vocals",
        "device": "cpu"
      },
      "output_dir": "absolute path"
    }

响应 status 只有 success、partial、failed。响应携带 backend、逻辑 artifact paths、notes、warnings 和结构化 error。错误字段是 code/stage/message/recovery；stdout/stderr 只作为日志，不被当作自然语言协议解析。Worker 产物路径相对于 output_dir，避免把本机用户名写入轻量 metadata。

Core Client 固定定位 workers/melody/.venv/Scripts/python.exe，使用参数数组、显式 cwd、shell=False 和 timeout；每次运行生成唯一 run/output 目录，并把 worker stdout/stderr 保存到被忽略的 temp/melody-runs/。

## Canonical Note Events v1

src/audio2violinscore/notes/schema.py 使用标准库 dataclass/JSON 实现：

- pitch_midi 为 0..127；
- onset_sec >= 0；
- offset_sec > onset_sec；
- confidence 为可选 [0, 1]；
- instrument/source/backend 为明确字符串；
- extensions 保留 Basic Pitch pitch bend 等未来兼容信息；
- 顶层保留 tempo: null、warnings 和 extensions。

本阶段不加入指法、弓法、把位、音域修正或后处理字段。Canonical JSON 是 worker 输出的结构化内部真值，不通过 MIDI 反解析生成。

## Environment boundaries

- src/audio2violinscore/doctor.py: Core/外部工具/worker version-import discovery。
- src/audio2violinscore/workers/protocol.py: request/result JSON validation。
- src/audio2violinscore/workers/melody_client.py: Core-to-worker transport and typed errors。
- workers/melody/worker.py: Demucs、Basic Pitch、模型缓存和 Canonical JSON 生成。
- workers/muscriptor/README.md: 未来设计说明；本阶段没有环境、包或权重。
- scripts/: 真实外部程序和合成链路 smoke；不属于普通单元测试。
- tests/: Core mock/monkeypatch 单元测试。
- reports/benchmarks/: 只允许小型、可审查、无用户音频的 metadata。
- temp/、output/、.venv 和 cache/: 运行时目录，禁止进入公开仓库。

## CPU/GPU policy

本阶段实际安装和调用全部为 CPU 路径，PyTorch 使用 CPU wheel，Demucs device=cpu，Basic Pitch 在 Python 3.10/Windows 使用 ONNX Runtime。doctor 仍探测 nvidia-smi，worker version JSON 仍报告 torch_cuda_available 和 ONNX providers；探测结果不自动触发 CUDA/cuDNN 安装。

## Deferred work

MuScriptor 只保留未来 Python 3.11 adapter、协议适配、模型来源和许可证核验点。正式 postprocess、router、MusicXML、指法/弓法和 benchmark 排名必须在后续阶段单独评审。