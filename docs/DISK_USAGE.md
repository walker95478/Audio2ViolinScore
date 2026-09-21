# Disk usage

测量日期：2026-09-21。目录大小按文件字节求和，数值以 GiB（2^30 字节）显示。运行产物全部位于 Git 忽略目录；本表只用于环境审计，不代表未来模型规模上限。

## Phase 1B 安装后实测

| 范围 | 路径 | 字节 | GiB | 说明 |
|---|---|---:|---:|---|
| 项目源码/文档/锁文件 | D:\软件\扒谱（排除 .git、两个 .venv、cache、temp、output） | 269,920 | 0.000 | 不含运行缓存 |
| Git 元数据 | D:\软件\扒谱\.git | 164,130 | 0.000 | 不属于提交工作内容 |
| Core .venv | D:\软件\扒谱\.venv | 35,951,859 | 0.033 | Phase 1A Python 3.11.15、pytest、Ruff |
| Melody .venv | D:\软件\扒谱\workers\melody\.venv | 1,549,445,401 | 1.444 | Python 3.10.20、CPU Demucs/Basic Pitch/PyTorch/ONNX |
| tools | D:\软件\扒谱\tools | 0 | 0.000 | 当前不存在 |
| uv cache | D:\软件\扒谱\cache\uv | 39,370,372 | 0.037 | Core bootstrap cache |
| Melody model cache | D:\软件\扒谱\cache\melody | 86,636,133 | 0.081 | htdemucs/Hugging Face cache；Git 忽略 |
| Torch cache | D:\软件\扒谱\cache\torch | 0 | 0.000 | 当前无独立 torch checkpoint |
| temp | D:\软件\扒谱\temp | 803,912 | 0.001 | smoke WAV、request/result、日志；Git 忽略 |
| output | D:\软件\扒谱\output | 2,949,189 | 0.003 | stems、MIDI、Canonical JSON；Git 忽略 |
| MuseScore Studio 4 | C:\Program Files\MuseScore 4 | 435,255,044 | 0.405 | 不含 MuseSounds |

项目源码/文档一项排除 __pycache__ 后仍属于同一量级；.pyc 文件由 .gitignore 排除。

## D: 盘

| 项目 | 字节 | GiB / 比例 |
|---|---:|---:|
| 可用空间（安装前 Phase 1B） | 119,287,009,280 | 111.09 GiB |
| 可用空间（worker 环境/模型/合成 smoke 后） | 119,169,175,552 | 110.98 GiB |
| 本阶段实测新增占用（粗略） | 约 1.45 GiB | 主要是 Melody .venv，模型缓存约 0.08 GiB |

每次新增 backend 或模型前必须重新测量 D 盘空间。CPU-only 选择没有下载 CUDA/cuDNN；后续若改用 GPU，需单独评估额外 wheel、驱动和磁盘占用。

## Git boundary

.venv、uv/Hugging Face cache、temp/、output/、音频、模型权重、生成 PDF/MIDI 和日志均由 .gitignore 排除。只允许在 reports/benchmarks/ 提交 JSON、Markdown 和小型文本 metadata。