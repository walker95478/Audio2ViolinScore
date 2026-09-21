# Workers

当前已实现 Melody Worker：

- 独立环境：workers/melody/.venv；
- CPU-only Demucs 4.1.0、Basic Pitch 0.4.0、PyTorch 2.1.2+cpu 和 ONNX Runtime；
- Core 通过 Worker Protocol v1 和 subprocess client 调用；
- 模型缓存和运行产物不进入 Git。

MuScriptor Worker 仍处于 not_installed / paused 状态，设计说明见 workers/muscriptor/README.md。每个 worker 必须使用自己的 workers/<name>/.venv，不复用 Core 或其他 worker 环境。