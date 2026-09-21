# MuScriptor worker（future / paused）

Phase 1B 只定义适配边界，不创建 MuScriptor 环境、不安装 Python 包、不下载模型权重，也不运行 MuScriptor 推理。

未来 worker 约定：

- 使用独立的 workers/muscriptor/.venv；
- 目标 Python 基线为 3.11，不能复用 Core 或 Melody .venv；
- 通过同一 Worker Protocol v1 接收绝对输入路径和 CPU/GPU options；
- 将后端原始结果转换为 Canonical Note Events v1，不把指法、弓法或把位字段提前塞入 Core schema；
- 在安装前核验 MuScriptor 代码、模型、依赖和生成文件的许可证及来源；
- 对模型缓存、临时产物、音频和生成 MIDI/PDF 使用 Git 忽略规则；
- 先完成轻量 --version --json import 检查，再单独设计合成音频 smoke。

当前状态：not_installed / paused。任何安装或权重下载都需要新的阶段授权。