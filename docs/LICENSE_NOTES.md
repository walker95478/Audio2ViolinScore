# License notes

本文件只记录当前实际引入或验证的组件，不构成未来商业使用的整体许可证清关。版权音频、模型权重和用户生成二进制不进入公开仓库。

## Core and external tools

| Component | Source/version | License/evidence |
|---|---|---|
| Python | uv-managed CPython 3.11.15 | 运行时解释器；以 CPython 发行条款为准。 |
| pytest | 8.4.2 | PyPI metadata reports MIT; development-only. |
| Ruff | 0.16.8 | PyPI metadata reports MIT; development-only. |
| FFmpeg | winget Gyan.FFmpeg, tested 8.1.1 | 外部 GPL-3.0 runtime；不作为 Python dependency 精确锁定。 |
| MuseScore Studio | winget Musescore.Musescore 4.7.5.260831071, CLI 4.7.5 | 外部 GPL-3.0 application；本阶段只验证 CLI→PDF，不安装 MuseSounds。 |

## Phase 1B worker packages

| Component | Version/source | License/evidence |
|---|---|---|
| Demucs | 4.1.0, PyPI / official repository | MIT；代码和模型来源需分别核验，模型权重只保存在被忽略缓存。 |
| Basic Pitch | 0.4.0, Spotify official repository | Apache-2.0；包许可证不自动等同于模型、训练数据或输入音频的商业许可。 |
| PyTorch | 2.1.2+cpu, official CPU wheel index | BSD-style/PyTorch license；本阶段只使用 CPU wheel。 |
| ONNX Runtime | 1.23.2 | MIT；本阶段使用 CPU execution path。 |
| soundfile | 0.14.0 | BSD-3-Clause；通过锁文件安装。 |
| setuptools | 80.10.2 | MIT；仅为 resampy 的 pkg_resources runtime import 提供兼容性。 |

参考来源：

- Demucs: https://pypi.org/project/demucs/
- Basic Pitch: https://github.com/spotify/basic-pitch
- PyTorch: https://github.com/pytorch/pytorch
- ONNX Runtime: https://github.com/microsoft/onnxruntime
- SoundFile: https://github.com/bastibe/python-soundfile

## Models and data

htdemucs 模型通过 Demucs 4.1.0 使用的官方 Hugging Face model path 获取，仅用于本地合成 smoke。模型权重不提交，模型来源、版本、使用条款和再分发限制仍需在产品化前单独核验。Basic Pitch 的代码许可证不代表任何商业歌曲、训练数据或导出乐谱都自动获得许可。

prom_dress-mxmtoon-prom_dress.mp3 当前不存在；本阶段没有下载或执行商业音频。正式处理任何音频前，必须确认用户拥有相应使用权。

## Not introduced

MuScriptor、TensorFlow、CUDA/cuDNN、MuseSounds、正式后处理、自动路由、指法/弓法模型和 benchmark 二进制均不在本阶段范围内。transitive dependencies 的完整版本由 workers/melody/uv.lock 记录，法律审查不能由锁文件替代。