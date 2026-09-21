# Audio2ViolinScore — Codex 施工方案

> 工作区：`D:\软件\扒谱`  
> 平台：Windows 11 x64  
> 目标：把本地音频文件中的主旋律，尽可能自动转换为适合小提琴演奏和继续编辑的五线谱。  
> 核心原则：**开源优先、本地运行、环境隔离、先 benchmark 再定默认路线、最终以 MusicXML/PDF 为交付而不是裸 MIDI。**

---

## 0. 项目目标

本项目不是“万能自动总谱生成器”，而是一个面向个人练琴场景的 **Audio → Violin Melody Score** 工具。

典型用例：

1. 用户拿到一首小众、跨界、OST、独立音乐等音频；
2. 网上没有可直接使用的小提琴谱；
3. 软件自动尝试提取主旋律；
4. AI 完成音高与节奏转录；
5. 自动做碎音清理、单声部化、节拍量化和小提琴音域适配；
6. 输出可继续编辑的 `MusicXML` / `MSCZ`，以及最终可打印的 `PDF`；
7. 用户只需要在 MuseScore 中做少量人工校正，然后直接练琴。

### 0.1 MVP 明确要做

- 输入：`mp3 / wav / flac / m4a`
- 两条可切换的转录 backend：
  - **Full-mix backend：MuScriptor**
  - **Melody backend：Demucs → Basic Pitch**
- 统一中间格式：`Canonical Note Events`
- 自动后处理：
  - 去除极短鬼音
  - 相邻同音碎片合并
  - 单声部化
  - 节拍/下拍感知量化
  - 小提琴最低音域检查
  - 可选整体八度调整
- 输出：
  - `raw.mid`
  - `cleaned.mid`
  - `notes.json`
  - `violin.musicxml`
  - `violin.pdf`
  - `report.json`
- 提供命令行入口
- 可以对同一首歌运行多条 pipeline 做 benchmark

### 0.2 MVP 暂时不做

- GUI
- 自动指法
- 自动把位
- 自动弓法
- 复杂和声编配
- 钢琴伴奏生成
- 管弦乐完整总谱
- 第二小提琴/同类多声部精确分离
- CUDA 优化
- Telegram 自动下载
- 商业化打包

---

# 1. 已确定的总体技术路线

项目不要 fork 一个现有大仓库直接魔改，而采用“**轻量 orchestrator + 独立 backend worker**”结构。

```text
                             Audio2ViolinScore
                                    │
                                    ▼
                            Core Orchestrator
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
             Melody Backend                  Full-Mix Backend
          Demucs → Basic Pitch                  MuScriptor
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
                         Canonical Note Events
                                    │
                                    ▼
                           Violin Postprocessor
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
       Fragment Merge        Monophonic Reduce       Noise Filter
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    ▼
                         Beat-aware Quantization
                                    │
                                    ▼
                         Violin Range Adaptation
                                    │
                                    ▼
                         MIDI + MusicXML Export
                                    │
                                    ▼
                              MuseScore 4+
                                    │
                                    ▼
                               PDF / MSCZ
```

---

# 2. 为什么采用双 backend

## 2.1 Melody Backend：Demucs → Basic Pitch

适合：

- 主唱旋律转小提琴
- 清晰的人声
- 纯小提琴独奏
- 萨克斯 / 二胡 / 吉他 solo
- 目标旋律可以先被较好隔离的情况

理由：

- Basic Pitch 对单乐器 / 单旋律输入更合适；
- Demucs 先把人声等目标声部抽出来，可以显著降低多乐器干扰；
- GitHub 上真实用户也反馈：先 stem separation 再 transcription，碎音和误识别往往更少。

## 2.2 Full-Mix Backend：MuScriptor

适合：

- 复杂器乐
- 跨界音乐
- OST
- 没有清晰 vocals 的歌曲
- 无法通过 Demucs 获得理想目标 stem 的情况

理由：

- MuScriptor 从设计上就是面向多乐器真实混音的自动音乐转录；
- 自带节拍检测、量化、MIDI 和乐谱输出；
- 支持 instrument conditioning；
- 当前项目仍活跃，测试与工程化程度明显高于很多个人项目。

## 2.3 不预设谁是默认 backend

第一阶段必须用真实歌曲 benchmark 后再决定：

- 人声歌曲默认是否走 Demucs + Basic Pitch；
- 复杂器乐是否默认走 MuScriptor；
- 是否可以自动路由；
- 是否保留“compare mode”。

---

# 3. 外部项目借鉴策略

## 3.1 MuScriptor

用途：**正式 backend**

建议：

- 优先通过稳定 CLI / Python API 调用；
- 不修改模型内部实现；
- 不把 MuScriptor 源码复制进本项目；
- 保持独立虚拟环境；
- 保留其 raw output，便于 debug。

注意：

- 代码许可与模型权重许可要分别记录；
- 当前模型权重仅用于非商业场景时，要在项目文档中明确。

---

## 3.2 demixer

用途：**只借鉴工程结构，不直接 fork**

重点学习：

- backend worker 隔离
- subprocess 协议
- stage-based pipeline
- artifact bundle
- benchmark / evaluation 设计
- 可选阶段失败后仍保留其他产物

不要直接以它作为项目基础，原因：

- 功能远超本项目需求；
- 当前运行依赖声明不完整；
- 多套 research worker 安装复杂；
- AGPL 许可没有必要引入。

---

## 3.3 song2score

用途：**产品思路参考，不作为核心依赖**

可参考：

- `vocals → violin` 的产品入口
- CLI 参数设计
- MusicXML instrument mapping

不要把 README 中的“Violin specialized transcription”视为已经解决小提琴转录，因为代码实现本质上仍主要依赖 Basic Pitch，且 tempo / time signature 等部分尚不完整。

---

# 4. Windows 环境设计

## 4.1 工作区

所有项目文件放在：

```text
D:\软件\扒谱
```

禁止污染：

- 系统 Python
- 用户现有 Python 3.12 环境
- 全局 site-packages
- 现有 AI / 开发项目环境

---

## 4.2 环境管理

优先使用：

```text
uv
```

如果机器未安装 `uv`，允许 Codex安装官方 `uv`。

建议三层环境：

```text
D:\软件\扒谱\
├─ .venv-core\
├─ workers\
│  ├─ melody\
│  │  └─ .venv\
│  └─ muscriptor\
│     └─ .venv\
```

推荐版本：

### Core

```text
Python 3.11
```

只安装轻量依赖：

- typer
- rich
- pydantic
- mido
- music21（如需要）
- numpy（如需要）
- pytest
- ruff

### Melody Worker

```text
Python 3.10
```

核心：

- Demucs
- Basic Pitch
- ONNX Runtime 优先
- soundfile
- ffmpeg 外部依赖

Baseline 建议：

```text
Demucs 4.1.x
Basic Pitch 0.4.x
```

Codex安装前必须实际核验当前 Windows 可用版本并 lock。

### MuScriptor Worker

```text
Python 3.11
```

安装当前稳定 MuScriptor release。

Baseline：

```text
MuScriptor 0.3.x
```

CPU-first。

### 禁止

MVP 阶段不要主动安装：

- CUDA Toolkit
- cuDNN
- TensorFlow（除非 Basic Pitch 当前 Windows 官方链路不可避免）
- MuseSounds
- Docker
- WSL
- Anaconda

---

# 5. 外部程序

## 5.1 FFmpeg

要求：

```powershell
ffmpeg -version
ffprobe -version
```

二者均可调用。

如果未安装：

- 使用官方可信发行方式安装；
- 不要把一个巨大静态包复制多份进各个 worker；
- 尽量作为系统级可执行程序供项目只读调用。

---

## 5.2 MuseScore Studio

要求：

```text
MuseScore 4+
```

作用：

- MIDI / MusicXML 检查
- 排版
- PDF 导出
- 最终人工修谱

MVP：

- 安装 MuseScore Studio 本体
- **不要安装 MuseSounds**
- Codex需要识别 `MuseScore4.exe` 实际路径
- 记录到项目配置，而不是假定 PATH 一定存在

必须做一次 CLI smoke test：

```text
MusicXML → PDF
```

并验证输出文件真实存在，不只看进程返回码。

---

# 6. 推荐项目目录

Codex先创建：

```text
D:\软件\扒谱
│
├─ README.md
├─ pyproject.toml
├─ uv.lock
├─ .gitignore
├─ .env.example
│
├─ docs\
│  ├─ ARCHITECTURE.md
│  ├─ ENVIRONMENT.md
│  ├─ BENCHMARK.md
│  └─ LICENSE_NOTES.md
│
├─ config\
│  ├─ default.yaml
│  └─ backends.yaml
│
├─ src\
│  └─ audio2violinscore\
│     ├─ __init__.py
│     ├─ cli.py
│     │
│     ├─ audio\
│     │  ├─ probe.py
│     │  └─ preprocess.py
│     │
│     ├─ workers\
│     │  ├─ protocol.py
│     │  ├─ melody_client.py
│     │  └─ muscriptor_client.py
│     │
│     ├─ notes\
│     │  ├─ schema.py
│     │  ├─ normalize.py
│     │  └─ validators.py
│     │
│     ├─ postprocess\
│     │  ├─ noise_filter.py
│     │  ├─ fragment_merge.py
│     │  ├─ monophonic.py
│     │  ├─ quantize.py
│     │  └─ continuity.py
│     │
│     ├─ violin\
│     │  ├─ range.py
│     │  ├─ transpose.py
│     │  └─ adapter.py
│     │
│     ├─ notation\
│     │  ├─ midi.py
│     │  ├─ musicxml.py
│     │  └─ musescore.py
│     │
│     ├─ pipeline\
│     │  ├─ runner.py
│     │  ├─ router.py
│     │  └─ artifacts.py
│     │
│     └─ benchmark\
│        ├─ runner.py
│        └─ metrics.py
│
├─ workers\
│  ├─ melody\
│  │  ├─ pyproject.toml
│  │  ├─ uv.lock
│  │  ├─ worker.py
│  │  └─ .venv\
│  │
│  └─ muscriptor\
│     ├─ pyproject.toml
│     ├─ uv.lock
│     ├─ worker.py
│     └─ .venv\
│
├─ tests\
│  ├─ unit\
│  ├─ integration\
│  └─ fixtures\
│
├─ samples\
│  └─ input\
│
├─ output\
├─ cache\
├─ temp\
└─ scripts\
   ├─ bootstrap.ps1
   ├─ doctor.ps1
   ├─ benchmark.ps1
   └─ disk_usage.ps1
```

---

# 7. Canonical Note Event 设计

所有 backend 最终统一输出同一种 JSON schema。

建议：

```json
{
  "schema_version": 1,
  "source": {
    "file": "song.mp3",
    "backend": "basic_pitch",
    "stem": "vocals"
  },
  "tempo": {
    "bpm": 96.0,
    "beats_per_bar": 4,
    "confidence": 0.91
  },
  "notes": [
    {
      "id": 1,
      "pitch_midi": 69,
      "onset_sec": 12.500,
      "offset_sec": 13.021,
      "confidence": 0.93,
      "instrument": "vocals"
    }
  ]
}
```

Core 后处理只认这个 schema。

不要让：

- Basic Pitch MIDI
- MuScriptor MIDI
- MusicXML

直接成为内部唯一真值。

---

# 8. 小提琴后处理层

这是本项目真正需要自主开发的核心。

## 8.1 Noise Filter

规则先简单可解释：

- 极短音符过滤；
- 超低 confidence 音符过滤；
- 静音附近孤立音符标记；
- 大跳且持续极短的音符作为疑似误识别。

所有阈值必须可配置。

禁止直接把“疑似错误音”永久删除而不记录。

`report.json` 需要记录：

```json
{
  "removed_notes": [],
  "flagged_notes": []
}
```

---

## 8.2 Fragment Merge

需要解决真实 AMT 常见问题：

```text
原本：A4 持续 1 秒
AI：  A4 0.45s + A4 0.50s
```

合并条件至少参考：

- pitch 相同；
- gap 小于某阈值；
- 位于同一 beat / phrase 邻域；
- velocity / confidence 接近。

必须支持：

```text
--merge-fragments conservative
--merge-fragments aggressive
--no-merge-fragments
```

---

## 8.3 Monophonic Reduction

小提琴主旋律默认单声部。

出现同时多个 pitch 时，不能随机取一个。

V1 可综合：

- confidence
- duration
- pitch continuity
- 与前后音距离
- instrument priority
- melodic salience

保留被丢弃候选，写入 debug report。

---

## 8.4 Quantization

不要简单：

```text
四舍五入到固定 1/16 秒
```

必须基于：

- BPM
- beat
- downbeat
- beat subdivision

MuScriptor 路线：

- 优先利用其已经生成的 beat grid / quantized result；
- Core 可做二次轻量修整。

Basic Pitch 路线：

- 使用 Beat This! 或复用可靠节拍检测结果；
- 再做 beat-aware quantization。

MVP 支持的最小网格：

```text
1/4
1/8
1/16
triplet（仅在检测可靠时）
```

---

## 8.5 Violin Range

小提琴最低开放弦：

```text
G3
MIDI 55
```

V1 设一个实用演奏上限，例如：

```text
E7 左右
```

但高音不应硬删除，只需 warning。

提供两种模式：

### Preserve Key

```text
--preserve-key
```

不改变原调。

低于 G3：

- 标记 warning；
- 不自动改单音。

适合和原曲一起拉。

### Fit Violin

```text
--fit-violin
```

只考虑：

```text
0
+12
-12
```

等整体八度变换，选择对整段旋律更合理的方案。

禁止逐音自动跳八度，否则会破坏旋律线。

---

# 9. CLI 目标

MVP 最终希望：

```powershell
a2vs "song.mp3"
```

自动运行推荐流程。

明确主唱：

```powershell
a2vs "song.mp3" --mode vocal
```

强制 MuScriptor：

```powershell
a2vs "song.mp3" --mode fullmix
```

只跑 Demucs + Basic Pitch：

```powershell
a2vs "song.mp3" --backend melody
```

只跑 MuScriptor：

```powershell
a2vs "song.mp3" --backend muscriptor
```

比较：

```powershell
a2vs "song.mp3" --mode compare
```

保留原调：

```powershell
a2vs "song.mp3" --preserve-key
```

自动适配小提琴：

```powershell
a2vs "song.mp3" --fit-violin
```

保留中间 stem：

```powershell
a2vs "song.mp3" --keep-temp
```

清理大型临时文件：

```powershell
a2vs cleanup
```

环境诊断：

```powershell
a2vs doctor
```

---

# 10. Phase 0 — 环境审计

Codex开始安装前先执行并记录：

```powershell
Get-ComputerInfo
python --version
py --list
git --version
ffmpeg -version
ffprobe -version
uv --version
where.exe python
where.exe ffmpeg
where.exe mscore
where.exe MuseScore4
nvidia-smi
```

并检查：

```powershell
Get-PSDrive D
```

输出：

```text
docs\ENVIRONMENT.md
```

至少记录：

- Windows 版本
- CPU
- RAM
- GPU
- 当前 Python
- 是否已有 uv
- FFmpeg 状态
- MuseScore 状态
- D 盘剩余空间

### Phase 0 验收

- 不修改现有 Python；
- 明确 D 盘剩余空间；
- 明确哪些依赖已存在；
- 确认工作区路径的中文字符不会造成 Python / subprocess 问题。

---

# 11. Phase 1 — Bootstrap

## 11.1 Core

创建：

```text
.venv-core
```

并完成：

```powershell
uv run pytest
uv run ruff check .
```

先建立最基础的：

```text
a2vs doctor
```

## 11.2 Melody Worker

建立独立 Python 3.10 环境。

完成 smoke tests：

1. Demucs import；
2. Basic Pitch import；
3. 10 秒测试音频 Demucs 分离；
4. 单声部 WAV → Basic Pitch；
5. 能写出 MIDI / JSON；
6. Core 能通过 subprocess 调 worker。

## 11.3 MuScriptor Worker

建立独立环境。

完成：

1. import；
2. model 权重下载；
3. 10 秒音频 CPU transcription；
4. JSONL / MIDI 输出；
5. Core subprocess 调用。

## 11.4 MuseScore

完成：

```text
test.musicxml
→ MuseScore CLI
→ test.pdf
```

并确认 PDF 文件真实存在。

---

# 12. Phase 2 — Benchmark First

**不要先写自动路由。**

先拿真实歌曲比较。

第一个样本建议：

```text
samples\input\prom_dress-mxmtoon-prom_dress.mp3
```

如果该文件不在本机此目录，等待用户复制，不要自动联网寻找替代版权音源。

至少运行：

### A

```text
full mix → Basic Pitch
```

仅作为低基线。

### B

```text
full mix → Demucs vocals → Basic Pitch
```

### C

```text
full mix → MuScriptor small
```

### D

```text
full mix → MuScriptor medium
```

输出：

```text
output\benchmark\prom_dress\
├─ A_basic_raw\
├─ B_demucs_basic\
├─ C_muscriptor_small\
├─ D_muscriptor_medium\
└─ comparison.json
```

---

# 13. Benchmark 指标

不要只看论文 F1。

这个项目以“最后能不能拿来练琴”为核心。

自动统计：

- note count
- notes/minute
- simultaneous-note ratio
- ultra-short-note ratio
- repeated same-pitch fragment ratio
- out-of-violin-range count
- pitch jump distribution
- transcription wall time
- peak RAM（能测则测）
- temp disk usage
- final artifact size

人工评价预留：

```json
{
  "melody_similarity": null,
  "rhythm_readability": null,
  "editing_effort": null,
  "playability": null,
  "notes": ""
}
```

不要让程序自行给“哪条路线最好”打最终主观分。

Phase 2 结束后，由用户看实际谱面再决定默认 backend。

---

# 14. Phase 3 — 后处理开发

顺序：

1. Note schema
2. Fragment merge
3. Monophonic reduction
4. Noise filtering
5. Beat-aware quantization
6. Violin range
7. MusicXML export
8. MuseScore render
9. report.json

每个模块必须有 unit tests。

重点建立合成 fixtures：

```text
tests\fixtures\
├─ repeated_fragments.json
├─ overlapping_notes.json
├─ short_ghost_notes.json
├─ below_g3.json
└─ octave_candidate.json
```

---

# 15. Phase 4 — End-to-End

最终要求：

```powershell
a2vs "samples\input\prom_dress-mxmtoon-prom_dress.mp3" --mode vocal
```

生成：

```text
output\prom_dress\
├─ source.json
├─ backend.json
├─ notes_raw.json
├─ notes_cleaned.json
├─ raw.mid
├─ cleaned.mid
├─ violin.musicxml
├─ violin.pdf
├─ report.json
└─ debug\
```

成功标准：

- PDF 可打开；
- MusicXML 可在 MuseScore 4 打开；
- 至少一条可辨认主旋律；
- 不出现大面积同时几十个音的异常；
- 不出现大量 1/64 / 1/128 式碎谱；
- 小提琴声部使用高音谱号；
- 音域超限被报告；
- 原始输出全部可追溯。

---

# 16. 错误处理原则

禁止：

```text
except Exception:
    pass
```

每一阶段失败必须：

- 写 stderr；
- 写结构化 error 到 report；
- 保留已经成功生成的 artifact；
- 给出可执行修复建议。

例如：

```json
{
  "stage": "musescore_render",
  "status": "failed",
  "reason": "MuseScore executable not found",
  "recovery": "Set MUSESCORE_PATH in config/backends.yaml"
}
```

---

# 17. Artifact 管理

每次 run 生成唯一 run id。

例如：

```text
output\prom_dress\20260921_113500\
```

manifest：

```json
{
  "run_id": "20260921_113500",
  "input_sha256": "...",
  "backend": "melody",
  "versions": {
    "demucs": "...",
    "basic_pitch": "...",
    "muscriptor": "...",
    "musescore": "...",
    "ffmpeg": "..."
  }
}
```

保证未来能复现。

---

# 18. 缓存策略

缓存：

- MuScriptor model weights
- Demucs model weights
- 下载的模型
- 可复用 stem（可选）

不要每次重复下载。

缓存位置必须明确记录：

```text
D:\软件\扒谱\cache
```

如第三方库强制使用用户目录缓存，也要在 `ENVIRONMENT.md` 中列出真实路径。

---

# 19. 磁盘空间预算

建议开工前：

```text
D 盘至少保留 12 GB 可用空间
```

开发期预估：

| 项目 | 粗略预算 |
|---|---:|
| Core | < 0.5 GB |
| Melody worker | 1–3 GB |
| MuScriptor worker | 2–4 GB |
| 模型缓存 | 1–3 GB |
| MuseScore | ~0.5 GB |
| 临时音频 / benchmark | 1–2 GB |
| 安装下载缓存 | 1–2 GB |

安装完成后必须真实统计。

生成：

```text
docs\DISK_USAGE.md
```

PowerShell 建议：

```powershell
Get-ChildItem "D:\软件\扒谱" -Recurse -File |
    Measure-Object -Property Length -Sum
```

还要分别统计：

```text
.venv-core
workers\melody\.venv
workers\muscriptor\.venv
cache
output
temp
```

---

# 20. 安全与环境约束

Codex必须遵守：

1. 禁止删除用户已有 Python；
2. 禁止修改用户已有项目环境；
3. 禁止全局 `pip install`；
4. 禁止擅自修改系统 PATH，除非确有必要且先说明；
5. 禁止自动安装 CUDA；
6. 禁止安装 MuseSounds；
7. 禁止下载不明第三方模型；
8. 所有外部下载记录来源；
9. 依赖版本 lock；
10. 每次大安装前检查剩余磁盘空间。

---

# 21. License 记录

创建：

```text
docs\LICENSE_NOTES.md
```

至少记录：

- MuScriptor code license
- MuScriptor model weights license
- Basic Pitch license
- Demucs license
- Beat This license
- MuseScore license
- FFmpeg build/license
- music21
- 本项目自身 license

当前仅以：

```text
个人、学习、非商业用途
```

为目标。

不因为依赖开源就自动认为所有模型都允许商业使用。

---

# 22. Git 策略

Phase 0 完成后初始化 git。

建议 commit：

```text
chore: initialize project structure
chore: add environment audit
feat: add worker protocol
feat: add melody backend
feat: add muscriptor backend
feat: add canonical note schema
feat: add violin postprocessor
feat: add musescore export
test: add prom dress benchmark harness
```

不要把以下内容提交：

```text
.venv*
cache\
temp\
output\
*.mp3
*.wav
*.flac
model weights
```

---

# 23. Codex 工作方式要求

## 必须

- 每阶段先读当前代码；
- 先写最小设计；
- 再实现；
- 每次实现后运行测试；
- 不因为一个包冲突就去升级整套依赖；
- 发生版本问题时先定位；
- 记录所有 workaround；
- 保持 backend 可替换；
- 保持所有生成 artifact 可追溯。

## 禁止

- 一次性写几千行“大一统脚本”；
- 所有逻辑塞进 `main.py`；
- 用裸 `subprocess` 字符串拼命令；
- Windows 路径不加正确 quoting；
- 把中文路径问题归咎于用户然后改目录；
- 未 benchmark 就决定默认模型；
- 为追求“一键”而隐藏错误。

---

# 24. 第一轮执行顺序

Codex拿到本文档后按以下顺序执行：

```text
1. 只审计系统，不安装
2. 输出 ENVIRONMENT.md
3. 检查 D 盘空间
4. 初始化 Git
5. 创建目录结构
6. 安装/确认 uv
7. 创建 .venv-core
8. 创建 melody worker
9. smoke test Demucs
10. smoke test Basic Pitch
11. 创建 MuScriptor worker
12. smoke test MuScriptor
13. 检测/安装 MuseScore 4
14. smoke test MusicXML → PDF
15. 统计磁盘占用
16. 编写 benchmark harness
17. 等待/使用 prom_dress 测试音频
18. 跑 A/B/C/D 四路线
19. 输出 comparison.json + 各自 PDF
20. 暂停，等待用户人工比较
21. 根据结果再决定默认 backend
22. 再开始 Violin Postprocessor 正式开发
```

---

# 25. 第一阶段暂停点

**非常重要：**

Codex跑完 benchmark 后不要继续擅自实现“自动选最佳 backend”。

必须先把：

```text
A_basic_raw
B_demucs_basic
C_muscriptor_small
D_muscriptor_medium
```

各自的：

- PDF
- MusicXML
- MIDI
- metrics
- processing time

整理好，让用户实际看谱、试听后再决定。

本项目优先优化“用户练琴体验”，不是论文 benchmark。

---

# 26. 最终理想体验

未来使用者只需要：

```powershell
a2vs "一首很喜欢但没有谱的歌.mp3" --mode vocal
```

几分钟后得到：

```text
violin.pdf
violin.musicxml
```

然后：

```text
打开 MuseScore
→ 修几个明显错误
→ 架谱
→ 🎻 开拉
```

---

# 27. Phase 0 给 Codex 的启动指令

Codex可直接从这里开始：

```text
你现在位于 Windows 11 工作区：

D:\软件\扒谱

请严格按照本目录中的《Audio2ViolinScore_Codex施工方案.md》执行。

先只进行 Phase 0 环境审计，不要立即安装所有依赖，也不要修改我现有的系统 Python 环境。

完成：
1. 系统与硬件审计；
2. Python / uv / Git / FFmpeg / MuseScore / GPU 状态检查；
3. D 盘剩余空间检查；
4. 检查中文路径兼容性；
5. 创建 docs\ENVIRONMENT.md；
6. 给出下一阶段精确安装计划和预计新增磁盘占用。

完成 Phase 0 后先向我汇报，再进入 Phase 1。
```

---

## 参考项目

- MuScriptor  
  `https://github.com/muscriptor/muscriptor`

- Demixer  
  `https://github.com/revoydotdev/demixer`

- song2score  
  `https://github.com/winjayran/song2score`

- Spotify Basic Pitch  
  `https://github.com/spotify/basic-pitch`

- Demucs  
  `https://github.com/facebookresearch/demucs`

- Beat This!  
  `https://github.com/CPJKU/beat_this`

- MuseScore Studio  
  `https://musescore.org/`

---

**当前施工结论：**

> 不重复造 AI 模型，不把所有依赖强塞进一个环境。  
> MuScriptor 负责完整混音智能转录，Demucs + Basic Pitch 负责清晰旋律精确打击，项目自己的核心价值放在“AI Note Events → 真正可读、可拉的小提琴谱”这一层。
