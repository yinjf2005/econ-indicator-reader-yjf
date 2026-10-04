#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量生成 5 张快读卡（v2.4 第三形态）+ 首屏图。

用法: python scripts/gen_briefs.py
只写 assets/cases/*_brief.md 与其 _figures/fig0_stat_cards.svg、fig2_timeline.svg；
主图 fig1_*.svg 由既有管线产出、这里只引用，不重画。

体量预算（Q3 已拍板，脚本自校验）：每卡 ≤60 行 / ≤1.3k 字符。
快读卡是给普通用户看的，不是审计底本：审计完整性由「回链 + check.py B1–B5」承载，
卡内不复制判定清单 J 与外源表 A/B，也不内嵌时效轴 SVG（改用文字表；
fig2_timeline.svg 仍生成，供附录 §L 记录与复用）。
"""
import os
import sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL, "scripts", "vizmath"))
from svg_chart import stat_cards, timeline, save  # noqa: E402

Cases = os.path.join(SKILL, "assets", "cases")

MAX_LINES = 60
MAX_CHARS = 1300


def B(slug, figs, title, one, stats, fig1, fig1_alt, fig1_note, fig_rows,
      pub, grade, asof, misreads, tl, nexts, construct=False):
    return dict(slug=slug, figs=figs, title=title, one=one, stats=stats,
                fig1=fig1, fig1_alt=fig1_alt, fig1_note=fig1_note,
                fig_rows=fig_rows, pub=pub, grade=grade, asof=asof,
                misreads=misreads, tl=tl, nexts=nexts, construct=construct)


CASES = [
    # ---------------- 教学 5 张（构造示例；真值回归基线已按用户决定清理，不入库） ----------------
    B(slug="demand", figs="demand_figures",
      title="需求领域 · 社零“除汽车”（构造示例）",
      one="“除汽车后只剩 +2.0%”是错的：汽车是拖累项，剔除后必然高于总额——正确是 +6.65%。",
      stats=[("社零同比", "+4.0%", "汽车权重 13.5% · 同比 −13.0%", "down"),
             ("除汽车增速", "+6.65%", "高于总额 2.65pp", "up"),
             ("汽车拉动", "−1.755pp", "13.5% × (−13.0%)", "down")],
      fig1="fig1_contrib_split.svg",
      fig1_alt="一根绿条（−1.755pp）抵掉 23% 正贡献",
      fig1_note="看那根绿条：拔掉后读数落在 +6.65%，不是 +2.0%。",
      fig_rows=[("汽车拉动", "−1.755pp", "抵掉正贡献 23%，故剔除后必然高于总额")],
      pub="教学构造", grade="T4×1", asof="2026-10-04（虚构）",
      misreads=["⚠ “除汽车只剩 +2.0%”方向写反了：剔除拖累项后必然高于总额。",
                "⚠ 1—2 月是合并累计同比，拿它判单月景气在方法上无效。"],
      tl=[("教学日 2026-10-04", "构造示例发布，无真实发布方", "发布"),
          ("2026-10 中旬", "9 月社零与季调环比", "下一步"),
          ("待定", "汽车类销量与均价，拆量 vs 价", "观察")],
      nexts=["补齐季调环比 → 双轨里“看边际动能”那条腿才有。",
             "补齐汽车类销量与均价 → 才能把 −13.0% 拆成量 vs 价。"],
      construct=True),

    B(slug="production", figs="production_figures",
      title="生产领域 · 工增 vs 发电量（构造示例）",
      one="工增 +6.5% 与发电量 +1.2% 的裂口 5.3pp 是物理量背离，先找机制（结构 / 口径 / 库存），别直接跳到“数据注水”。",
      stats=[("工增同比", "+6.5%", "发电量 +1.2% · 裂口 5.3pp", "up"),
             ("发电量同比", "+1.2%", "同向为负则背离成立", "down"),
             ("PMI 官方 vs 财新", "49.5 vs 51.0", "50 是分界，不是好坏", "flat")],
      fig1="fig1_gap_diverge.svg",
      fig1_alt="工增与发电量裂口 5.3pp",
      fig1_note="裂口来自量纲不同（增加值 vs 电量），这张图只做同向性检验。",
      fig_rows=[("工增 − 发电量", "5.3pp", "量纲不同：增加值 vs 电量，只做同向性")],
      pub="教学构造", grade="T4×1", asof="2026-10-04（虚构）",
      misreads=["⚠ 两个量纲不同，裂口只做同向性检验，不能读成“高增长不需要电”。",
                "⚠ PMI 50 是扩张/收缩分界，不是好坏分界。"],
      tl=[("教学日 2026-10-04", "构造示例发布，无真实发布方", "发布"),
          ("2026-10 中旬", "9 月工增与发电量裂口", "下一步"),
          ("待定", "粗钢 / 水泥 / 货运量，做同向交叉", "观察")],
      nexts=["高耗能降速且单位电耗同步下行 → 结构效应坐实，裂口不是注水。",
             "粗钢、水泥、货运量也低且与电量同向 → “读数偏高”那条判定被削弱。"],
      construct=True),

    B(slug="prices", figs="prices_figures",
      title="物价领域 · CPI 翘尾拆分（构造示例）",
      one="“通胀起来了”是错的：+0.5% 里翘尾占 +0.7%，新涨价其实是 −0.2%——趋势没转，边际已在收缩。",
      stats=[("CPI 同比", "+0.5%", "翘尾 +0.7% + 新涨价 −0.2%", "up"),
             ("新涨价", "−0.2%", "动能为负", "down"),
             ("核心 CPI", "+0.8%", "高于整体 → 波动来自食品", "up")],
      fig1="fig1_qiwei_split.svg",
      fig1_alt="新涨价那一格为负",
      fig1_note="看新涨价那一格为负：当期无新增涨价压力，涨幅全来自去年基数。",
      fig_rows=[("新涨价", "−0.2%", "翘尾 +0.7% 之下的当期动能")],
      pub="教学构造", grade="T4×1", asof="2026-10-04（虚构）",
      misreads=["⚠ “通胀起来了”是错的：新涨价已为负，边际在收缩。",
                "⚠ 核心高于整体，说明波动来自食品，不是全面通胀。"],
      tl=[("教学日 2026-10-04", "构造示例发布，无真实发布方", "发布"),
          ("2026-10 上旬", "9 月 CPI 翘尾与新涨价", "下一步"),
          ("待定", "中下游转嫁与需求", "观察")],
      nexts=["未来 3 个月新涨价转正且累计 ≥+0.3% → “边际收缩”被改写。",
             "核心 CPI 连续 3 月 ≥+0.8% 且食品回落 → 扰动升级为趋势。"],
      construct=True),

    B(slug="finance", figs="finance_figures",
      title="金融领域 · 社融 surprise（构造示例）",
      one="“社融超预期但股市跌”不是市场犯错，是总量 surprise 与质量 surprise 不同号——市场只对偏离定价。",
      stats=[("社融存量同比", "9.6%", "共识 9.3% · surprise +0.3pp", "up"),
             ("M1−M2 剪刀差", "−3.0pp", "2 月走阔至 −9.5pp", "down"),
             ("资产反应", "股跌 / 债强", "与总量 surprise 不同号", "flat")],
      fig1="fig1_surprise_gap.svg",
      fig1_alt="实际与共识之间那 0.3pp",
      fig1_note="实际与共识之间那 0.3pp 就是市场当天定价的东西，别当利好确认。",
      fig_rows=[("超预期幅度", "+0.3pp", "9.6% − 共识 9.3%，即当日定价内容")],
      pub="教学构造", grade="T4×1", asof="2026-10-04（虚构）",
      misreads=["⚠ 社融 ≠ M2：两种“差”不能混用；剪刀差走阔先看春节错位。",
                "⚠ 1—2 月单月剪刀差在方法上不可用，不可用单月判“资金活化恶化”。"],
      tl=[("教学日 2026-10-04", "构造示例发布，无真实发布方", "发布"),
          ("2026-10 中旬", "9 月社融与 M1−M2", "下一步"),
          ("待定", "企业中长贷与政府债同向性", "观察")],
      nexts=["企业中长贷与政府债同向走强 → “质量 surprise 为负”被削弱。",
             "两月平均后剪刀差回到 −6pp 内 → 单月走阔降级为季节性。"],
      construct=True),

    B(slug="fiscal", figs="fiscal_figures",
      title="财政领域 · 赤字率口径（构造示例）",
      one="“赤字率没提 = 财政没加力”是口径错误：狭义 3.0% 之外，调入与专项债等广义支出也要算，实际约 3.38%。",
      stats=[("狭义赤字率", "3.00%", "口径未变 · 不等于没加力", "flat"),
             ("调入资金折算", "+0.38pp", "GDP 130 万亿 · 0.5 万亿", "down"),
             ("实际赤字率", "3.38%", "广义口径 · 高 0.38pp", "up")],
      fig1="fig1_deficit_gap.svg",
      fig1_alt="狭义到实际的 0.38pp 口径差",
      fig1_note="0.38pp 是口径差（调入资金），不是四舍五入，也不是新增风险。",
      fig_rows=[("狭义 → 实际", "+0.38pp", "调入资金折算，非新增风险")],
      pub="教学构造", grade="T4×1", asof="2026-10-04（虚构）",
      misreads=["⚠ 赤字率没提 ≠ 财政没加力：狭义口径漏掉调入、专项债等广义工具。",
                "⚠ 专项债放量不等于形成投资：资金到位到实物工作量有 1—2 季时滞。"],
      tl=[("教学日 2026-10-04", "构造示例发布，无真实发布方", "发布"),
          ("2026-10 下旬", "9 月财政收支与专项债投向", "下一步"),
          ("待定", "水泥 / 挖掘机 / 沥青开工，看资金落地", "观察")],
      nexts=["专项债资本金、政策性金融工具还有别的广义项 → 广义赤字上修。",
             "水泥、挖掘机、沥青开工 1—2 季内同步回升 → “时滞”坐实，不是空转。"],
      construct=True),
]

SYMBOL_LINE = "符号：§ 附录小节 ｜ T1–T4 信源分级 ｜ pp 百分点 ｜ ⚠ 误读"
# 「○ 未检索」只在构造示例卡里出现（真值卡有 T1 一手源，无未检索项）。
# 现库内 5 张全部为构造示例（construct=True），故默认走带 ○ 的那一版；
# construct=False 留给临时真值卡，可省这 6 个字符。
SYMBOL_LINE_CONSTRUCT = SYMBOL_LINE + " ｜ ○ 未检索"


def tab(head, rows):
    return [head, "|---|---|---|"] + list(rows)


def interleave(xs, sep=""):
    """在相邻元素之间插入 sep（空串 = 空行），保证 markdown 不会把两行并成一段。"""
    out = []
    for i, x in enumerate(xs):
        out.append(x)
        if i < len(xs) - 1:
            out.append(sep)
    return out


def build(c):
    figs = os.path.join(Cases, c["figs"])
    os.makedirs(figs, exist_ok=True)
    save(stat_cards([(a, b, d, e) for a, b, d, e in c["stats"]],
                    title="30 秒数字卡 · " + c["title"],
                    subtitle="as-of " + c["asof"]),
         os.path.join(figs, "fig0_stat_cards.svg"))
    save(timeline(c["tl"], title="时效轴 · " + c["title"]),
         os.path.join(figs, "fig2_timeline.svg"))

    blocks = []
    blocks.append(["# 快读卡 · " + c["title"],
                   "> 结论层 [主卡](./%s.md) ｜ 审计底本 [附录](./%s_appendix.md) ｜ as-of %s · %s %s"
                   % (c["slug"], c["slug"], c["asof"], c["pub"], c["grade"])])
    if c["construct"]:
        blocks.append(["🚨 构造示例：非真实发布数据，标 %s、as-of 构造日、补数项未检索（○），"
                       "不可用于真实决策。" % c["grade"]])
    blocks.append(["<!-- VISUAL:START -->", "> " + c["one"]])
    blocks.append(["## 1 核心数字",
                   "![核心数字 · %s](./%s/fig0_stat_cards.svg)" % (c["title"], c["figs"])]
                  + tab("| 指标 | 读数 | 对照 |",
                        ["| %s | %s | %s |" % (a, b, d) for a, b, d, _ in c["stats"]]))
    blocks.append(["## 2 主图",
                   "![%s](./%s/%s)" % (c["fig1_alt"], c["figs"], c["fig1"])]
                  + tab("| 分解项 | 数值 | 说明 |",
                        ["| %s | %s | %s |" % r for r in c["fig_rows"]]))
    blocks.append(["> 读图：" + c["fig1_note"]])          # 独立块：表格后留空行
    blocks.append(interleave(["## 3 不能读成什么"] + list(c["misreads"])))
    blocks.append(["## 4 时效轴"]
                  + tab("| 时点 | 事件 | 性质 |", ["| %s | %s | %s |" % r for r in c["tl"]]))
    blocks.append(["## 5 下一步看什么"] + ["- " + n for n in c["nexts"]])
    blocks.append(["<!-- /VISUAL:END -->",
                   "**审计锚点**：判定 → [主卡](./%s.md) §2 ｜ 外源 → [附录](./%s_appendix.md) §K ｜ 图源 → 附录 §L ｜ 校验 B1–B5"
                   % (c["slug"], c["slug"]),
                   "**免责**：阈值未校准，不得当概率；不预测、非投资建议。"])
    blocks.append(["<!-- SYMBOLS:START -->",
                   SYMBOL_LINE_CONSTRUCT if c["construct"] else SYMBOL_LINE,
                   "<!-- /SYMBOLS:END -->"])

    text = "\n\n".join("\n".join(b) for b in blocks)

    path = os.path.join(Cases, c["slug"] + "_brief.md")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path, text


if __name__ == "__main__":
    bad = 0
    for c in CASES:
        p, t = build(c)
        n, ch = t.count("\n") + 1, len(t)
        flag = "  ← 超预算" if (n > MAX_LINES or ch > MAX_CHARS) else ""
        bad += bool(flag)
        print("%-42s %3d 行 %5d 字符%s" % (os.path.basename(p), n, ch, flag))
    print("预算 ≤%d 行 / ≤%d 字符 —— 超标 %d 张" % (MAX_LINES, MAX_CHARS, bad))
