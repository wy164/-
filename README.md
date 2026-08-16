# 斗地主 · 人机对战 (Dou Dizhu · Human vs. AI)

> **Dou Dizhu (Fight the Landlord)** — a classic Chinese card game in Python.
> You play against two computer opponents with full standard rules, scoring,
> and optional background music. Built purely on the Python standard library
> (tkinter) with **zero third-party dependencies**.

经典斗地主桌面小游戏：1 名真人玩家对战 2 个电脑 AI，标准斗地主规则 + 完整计分 + 可选背景音乐，纯 Python 标准库（tkinter）实现，无需安装任何第三方依赖。

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 特性 Features

- **1 真人 vs 2 电脑 AI**，出牌按逆时针顺序（你 → 右家 → 左家），你和另一位农民配合对抗地主。
- **完整牌型**：单张、对子、三张、三带一、三带二、顺子（≥5 张）、连对（≥3 对）、飞机（不带/带单/带对）、四带二、炸弹、王炸。
- **AI 决策**：按牌力叫地主；出牌时优先甩小牌、能一手走完就果断走、队友在管牌时让队友出、关键时刻用炸弹/王炸抢回出牌权。
- **完整计分**：叫分 × 炸弹倍数 × 春天/反春倍数，跨局累计总分实时显示，三方得分之和恒为 0。
- **图形界面**：tkinter 纯标准库绘制，圆角牌面 + 木质外框 + 桌面绿，支持高 DPI 缩放与全屏（F11）。
- **可选背景音乐**：放一个音频文件即可自动循环播放（Windows MCI，零依赖）；无音乐文件则静默跳过。
- **自带测试**：规则自测（牌型识别/比较/枚举一致性 + 30 局随机模拟）与 GUI 整局自动冒烟测试。

## 环境要求 Requirements

- **Python 3.8+**（内置 tkinter，无需 pip 安装任何东西）
- 在 **Windows** 上体验最佳：背景音乐使用系统自带 MCI，窗口支持高 DPI 缩放；
  其他平台（macOS / Linux）可正常运行游戏，但没有背景音乐（相关调用会自动跳过）。

## 快速开始 Quick Start

克隆（或下载）仓库后，进入**仓库根目录**执行：

```bash
# 推荐：直接双击运行main代码
python game/main.py

# 或作为包运行
python -m game.main
```

如果系统里同时装了多个 Python，请使用带 tkinter 的 Python（如官方安装包或 Anaconda 的 python.exe），而不是 Windows 商店版精简 Python。

> 注：项目按 `game` 包组织，必须在仓库根目录下运行以上命令（而非在 `game` 目录内部运行 `python main.py`）。

### 运行测试 Tests

```bash
# 规则自测：牌型识别、比较、出牌枚举一致性 + 30 局随机对局模拟
python game/test_rules.py

# GUI 冒烟测试：创建窗口并自动打完整局，验证绘制与流程无异常
python game/smoke_test.py
```

## 操作说明 Controls

- **全屏**：按 `F11` 或点右下角「全屏」按钮切换全屏/窗口，按 `Esc` 退出全屏。若想启动时直接全屏，把 [gui.py](gui.py) 顶部的 `FULLSCREEN_START` 改为 `True`。
- **叫地主**：轮到你在下方按钮区选择「叫 1/2/3 分」或「不叫」，叫分高者成为地主并获得 3 张底牌；三家都不叫会重新发牌。
- **出牌（逆时针）**：出牌顺序为 **你 → 右家 → 左家 → 你**。鼠标点击手牌选中/取消（选中的牌会抬高），然后点「出牌」；管不上时点「不出」；拿不准就点「提示」让电脑帮你选。
- 地主独享 3 张底牌并先出。农民（你和另一位电脑）互相配合，先出完牌的一方获胜。
- 出牌过程中显示各家在当前这一轮出的牌；某家过牌时自动撤下其上一轮的牌并提示「不出」，新一轮开始桌面清空。牌局结束后会在画布上方缩小、横向铺开公示两家电脑的剩余手牌。
- 顶部显示底牌，左下角「新一局」可随时重开（计分继续累计），右下角「音乐」可开关背景音乐。

## 背景音乐 Background Music（可选）

在**仓库根目录**或 **`game` 目录**下放一个 MP3 / WAV / M4A / FLAC 音频文件，启动游戏时即自动作为背景音乐循环播放，无需任何配置；找不到音频文件则静默跳过。可在界面右下角「音乐」按钮随时开关。

## 项目结构 Project Structure

```
.
└── game/
    ├── main.py          程序入口（含 Windows 高 DPI 设置）
    ├── gui.py           tkinter 图形界面与交互
    ├── game_logic.py    对局流程：叫地主、出牌、胜负与计分判定
    ├── rules.py         牌型识别、比较、出牌枚举
    ├── ai.py            电脑的叫地主与出牌决策
    ├── cards.py         牌的定义、点数比较、排序
    ├── audio.py         背景音乐播放（Windows MCI，零依赖）
    ├── test_rules.py    规则自测
    └── smoke_test.py    GUI 整局自动冒烟测试
```

## 游戏规则 Rules

- 共 54 张牌，三人各 17 张，留 3 张底牌。
- 牌型：单张、对子、三张、三带一、三带二、顺子（≥5 张，不含 2 和王）、连对（≥3 对）、飞机（不带/带单/带对）、四带二、炸弹、王炸。
- 炸弹可压任何非炸弹牌型；王炸最大。
- 出牌按**逆时针**顺序：你 → 右家 → 左家 → 你。

## 计分规则 Scoring

每局结束后弹出计分面板，显示本局明细并计入跨局累计总分（右上角实时显示）。

- **底分** = 叫地主时的分数（1/2/3 分）。
- **倍数**：每打出一个炸弹或王炸 ×2；出现「春天」或「反春」再 ×2。
  - 春天：地主获胜且农民一张牌都没出。
  - 反春：农民获胜且地主只出了一手牌。
- **结算**：地主赢则地主得「底分 × 倍数」×2，两位农民各扣「底分 × 倍数」；农民赢则相反（每位农民各得，地主扣双份）。三方得分之和恒为 0。
- 例：底分 2、出过 1 个炸弹、春天 → 单份 = 2×2×2 = 8，地主 +16，农民各 −8。

## 许可证 License

本项目采用 [MIT](LICENSE) 许可证开源。
