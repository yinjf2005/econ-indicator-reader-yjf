# econ-indicator-reader · 经济指标解读参考（读数层）

> 把一个**宏观读数**变成一条**可论证的经济语义**。
> 本包**完全自足**：公式出口、图表出口及其依赖、ima 投喂通道、四书镜像全部在包内，解压即用。
> 契约与自检细则一律以 **`SKILL.md`** 为准（本文只讲安装与上手，不复制契约）。

- 版本：v2.4（2026-10-04）｜契约底本：《经济指标解读操作指引 v2.0》`references/00-guide-full.md`
- 安装位置：用户级 `~/.workbuddy/skills/econ-indicator-reader/`

## 一、它回答什么 / 不回答什么

**回答**：这个数怎么读 —— 口径、可信度、在结构中处于什么位置、市场已定价了什么、能据此下什么结论。

**不回答**（会显式拒绝或转出）：预测下月数值（改给情景树与触发条件）／买卖加仓（降级为条件式情景 + 非投资建议，个股盯盘转 `a-share-fvt-watch`）／行情与机构观点聚合（转 `finance-wscn-brief`）／论文模型选型（转 `econpaper-architect`）／经济想法转数学（转 `econ-math-mapper`）。
分工与边界表见 `SKILL.md` §一–§二，此处不重复。

## 二、安装

```bash
# 方式 A：解压到用户级技能目录
unzip econ-indicator-reader.zip -d ~/.workbuddy/skills/
# 方式 B：把 econ-indicator-reader/ 整个目录拷进 ~/.workbuddy/skills/
```

安装后自检（预期 10 条全过）：

```bash
cd ~/.workbuddy/skills/econ-indicator-reader
python scripts/check.py --assets     # 自足性：文件齐备 / 无技能外资产引用 / 依赖探测
python scripts/check.py --selftest   # 契约回归：golden set 20 条 + 5 张教学卡 + 5 张快读卡
```

## 三、目录骨架

完整用途索引见 `SKILL.md` §八；此处只列常摸到的部分。

```
scripts/            # 全部可执行资产（标准库即可跑，主路径零外部依赖）
├── check.py            H1–H6 / V1–V12 / B1–B5 校验，--selftest / --assets
├── gen_briefs.py       批量生成 5 张快读卡 + 首屏图（自带体量预算校验）
├── card_preview.py     md → 单页折叠 HTML 预览（主卡 / 快读卡两形态）
├── ingest_books.py     ima 投喂通道（--keyword / --media-id / --list）
└── vizmath/            公式（tex2omml）+ 图表（svg_chart 零依赖 / render_figure 走 matplotlib）
assets/
├── interpretation_card.md / brief_card.md   主卡 / 快读卡模板
├── golden_set.jsonl                         自测集 20 条（10 正 10 负）
└── cases/              五领域教学案例各 1 例（production / demand / prices / finance / fiscal）
references/        规程与书库镜像（01–08 分册 + books/ 四层），契约细节不在此重复
```

## 四、怎么用（默认快通道）

给一个读数，一次性出**三件套**：`快读卡`（30 秒读完，给普通读者）＋ `主卡`（结论层，给决策者）＋ `附录`（七步 SOP 全量，给复核者）。例：

> "某月 CPI 同比 +0.5%、环比 −0.2%，怎么读？"

仅当关键前提缺失（口径未知 / 无共识预期 / 指标超纲 / 无发布方与时点）才切**澄清模式**补问 2–3 个问题。七步 SOP、硬阻断与输出契约见 `SKILL.md` §四–§五。

```bash
python scripts/check.py 解读卡.md          # 出稿前必跑；全 PASS 才能交付
python scripts/check.py 解读卡.md --json   # 机器可读
```

## 五、公式与图表出口

- **正文公式** → `scripts/vizmath/tex2omml.py`（pandoc → 原生 OMML）。**禁贴公式图片**；公式内不得含中文（会变方框）。
- **数据图表** → 默认 `scripts/vizmath/svg_chart.py`（**零依赖**，永远可用）；出版级走 `render_figure.py`（matplotlib，本环境未装）。
- 涨红跌绿（中国惯例），货币符号 ¥；每张图 ±6 行内必配数表。

```python
import sys, os
sys.path.insert(0, "scripts/vizmath")
from tex2omml import omml_for, add_math_run      # 公式
from render_figure import figure_context         # 图表（ctx.export 须在 with 块内）
```

## 六、扩展：投喂新书摘

新件落 `references/books/_inbox/`（粘贴 md，或 `python scripts/ingest_books.py --keyword "房地产"` 拉取）→ 判层移入对应书目录 → 更新 `books/_MIRROR_INDEX.md`（`○`→`✔`）→ 带来新方法时增补 `05-expectation-layer.md` / `07-pitfalls.md` → 跑 `python scripts/check.py --selftest`。
ima 知识库：`kb_id = ehrOmGP5tNL1aooI-8Dm6GaSpQqpkk3SdsEWC2n9lyQ=`（ima 主库 › 02_高频调用库 › 01_工作方法 › 经济理论模型库 › 专题-经济指标解读）。

## 七、诚实边界

四书蒸馏：欧乐鹰《解读中国经济指标》（读）、李奇霖《宏观经济数据分析手册》（机制，数据截至 2019–2020）、鲍莫尔《经济指标解读》（预期）、中村力《魔鬼分析学》（方法）。

- 字典口径与发布方以**官方最新公告**为准；技能内数值仅作示例，教学示例标【示例·非真实】；
- 未经官方核验的二手转引须逐条标注；verdict 阈值**未经回测校准**，必须附"未校准"声明，不得当概率使用。
