#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check.py —— econ-indicator-reader 硬阻断校验与自测。

用法:
  python scripts/check.py <解读卡.md> [--json]     # 自动发现同名 <stem>_appendix.md 合并校验
  python scripts/check.py <主卡.md> <附录.md>      # 显式指定双层两文件
  python scripts/check.py --selftest               # 契约自测（golden set + 案例库结构）
  python scripts/check.py --assets                 # 自足性校验（配套资产与依赖是否齐备）

退出码: 0 = 全部通过（含 WARN）；1 = 存在 FAIL；2 = 用法/文件错误。

对 *_brief.md 走**快读卡契约**：只跑 B1–B5（首屏存在 / 误读警示首屏 / 时效轴 /
图配数表+alt / 审计锚点回链+符号自解释），不跑双层 H/V——
快读卡**不含**判定清单与外源表 A/B，审计完整性由**回链 + 本校验集**承载。

双层契约 v2.1：
  Part 1 结论层（面向决策）+ Part 2 附录层（七步 SOP 全量）。**两文件缺一时脚本自动合并。**
  H1–H6 = 硬阻断（H6：结论层外源信源 T1–T4 须同行可追溯到发布时点）；
  V1–V12 = 结构层 WARN（不改退出码，但交付前必须消除或书面说明理由）。
  V8 = 符号表闭合：结论层用到的每个编号/单位/标记，都必须在 <!-- SYMBOLS --> 符号表内登记。
  V9 = 外源检索闭环：§3 外源印证 + N 项检索状态 + 附录 §K 检索日志 + 口径三角。
  V10 = 首屏可读性契约（读数表 + 误读警示 + 下一步 必须在首屏）。
  V11 = 折叠契约（判定清单 / 表 A·B / 口径三角等专业大表不得占首屏，须折叠或下沉）。
  V12 = 视觉契约（每张图须 alt 文本 + 数表 + 「读图：」一句 + 来源/as-of/T级）。

交付动作（v2.1 强制）：校验通过后脚本会打印 next_actions，其中第一项是
  **主动询问用户是否生成单页折叠 HTML 预览**——不得静默等待用户发现该能力。

说明: --selftest 校验的是**契约完整性**（golden set 字段齐全、正负配比、案例库五领域齐备），
      属于可机械判定的回归；语义正确性需用真实调用验证，不在本脚本范围内。
"""
import argparse
import json
import os
import re
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(SKILL_DIR, "assets", "golden_set.jsonl")
CASES = os.path.join(SKILL_DIR, "assets", "cases")

# H 项 -> (名称, 需要同时命中的关键字组)
RULES = {
    "H1": ("读数四问齐备", [["基期"], ["季调"], ["年化"], ["名义", "实际"]]),
    "H2": ("L2 语义 JSON 必标字段", [["stock_flow", "存量"], ["nominal_real", "名义"],
                                     ["time_frame", "时间框架"], ["endogeneity", "外生"]]),
    "H3": ("verdict 依据链与未校准声明", [["verdict"], ["依据"], ["未校准"]]),
    "H4": ("预期差已算或已声明无共识", [["surprise", "预期差"], ["共识", "surprise"]]),
    "H5": ("来源可追溯", [["发布方", "来源"], ["发布", "时点"]]),
}
FIELDS = ["结论", "读数四问", "结构归位", "双轨解码", "信源", "预期差", "对照", "verdict"]
# 双层契约 v2.0：Part 1 结论层必备锚点（落在主卡）
PART1_FIELDS = ["分层结论", "判定清单", "读数四问", "verdict"]
# 结构层红线
MAX_JUDGMENTS = 5      # V3 判定条目上限
MAX_LISTING_LINES = 20  # V4 判定清单区行数上限
MAX_PART1_RATIO = 0.50  # V2 结论层占总篇幅上限（> 此值 = 主次颠倒）
IMG_TABLE_WINDOW = 6    # S6 图周围多少行内必须出现数表
FIRST_SCREEN_LINES = 45  # V10/V11 首屏窗口：结论层前 N 行（约一屏半）

# --- v2.4 快读卡契约（第三形态）：<stem>_brief.md
BRIEF_FIELDS = {
    "B1": ("快读卡首屏存在", ("核心数字", "一句话结论")),
    "B2": ("误读警示在首屏", ("不能读成", "⚠")),
    "B3": ("时效轴存在", ("时效轴", "下一步")),
}

# --- V8 符号体系：结论层用到的编号/单位/标记，必须在符号表内登记
# 闭合标签允许 `<!-- SYMBOLS:END -->` 与 `<!-- /SYMBOLS:END -->` 两种写法（历史模板两种都出现过）
SYMBOL_BLOCK_RE = re.compile(r"<!--\s*/?\s*SYMBOLS:START\s*-->(.*?)<!--\s*/?\s*SYMBOLS:END\s*-->", re.S)
# v2.4 快读卡首屏契约区：<!-- VISUAL:START --> … <!-- /VISUAL:END -->
VISUAL_BLOCK_RE = re.compile(r"<!--\s*VISUAL:START\s*-->(.*?)<!--\s*/VISUAL:END\s*-->", re.S)
# (族名, "结论层是否用到"的正则, "符号表是否已定义"的正则)
SYMBOL_FAMILIES = [
    ("J=判定",   re.compile(r"(?<![A-Za-z0-9])J\d+"),            re.compile(r"J\d")),
    ("SC=情景",  re.compile(r"(?<![A-Za-z0-9])SC-\d+"),          re.compile(r"SC-")),
    ("N=补数",   re.compile(r"(?<![A-Za-z0-9])N\d+"),            re.compile(r"N\d")),
    ("§=附录",   re.compile(r"§[A-L](?:\.\d+)?"),                re.compile(r"§")),
    ("T=信源分级", re.compile(r"(?<![A-Za-z0-9])T[1-4](?![0-9])"), re.compile(r"T1")),
    ("H=硬阻断", re.compile(r"(?<![A-Za-z0-9])H[1-5](?![0-9])"), re.compile(r"H1")),
    ("V=结构校验", re.compile(r"(?<![A-Za-z0-9])V[1-8](?![0-9])"), re.compile(r"V1")),
    ("S=七步SOP步骤", re.compile(r"(?<![A-Za-z0-9])S[1-7](?![0-9])"), re.compile(r"S1")),
    ("A–D=闸门", re.compile(r"闸门"),                            re.compile(r"闸门")),
]
EXTRA_TOKENS = [
    ("pp=百分点", re.compile(r"(?<![A-Za-z])pp(?![A-Za-z])"),     re.compile(r"pp")),
    ("SA=季调",   re.compile(r"(?<![A-Za-z])SA(?![A-Za-z])"),     re.compile(r"SA")),
    ("P0–P2=优先级", re.compile(r"(?<![A-Za-z0-9])P[012](?![0-9])"), re.compile(r"P0")),
    ("⚠=易误读", re.compile(r"⚠"),                               re.compile(r"⚠")),
]
# 废止编号：情景曾用 S-A/B/C，与结构校验 V1–V9 撞名
LEGACY_SCENARIO_RE = re.compile(r"(?<![A-Za-z0-9])S-[A-C](?![0-9A-Za-z])")

# --- v2.3 外源检索闭环：H6 硬阻断 + V9 软校验
T_BADGE_RE = re.compile(r"(?<![A-Za-z0-9])T[1-4](?![0-9])")
# 发布时点：2026-09-30 / 2026年9月30日 / 2026-09 / 2026年9月 / 2026/09/30
DATE_RE = re.compile(r"(20\d{2})\s*[-/年.]\s*(\d{1,2})")
# 补数项检索状态标记
STATUS_MARKS = ("✅", "⚠", "○")

# 自足性：技能必须自带、不得依赖技能目录之外的文件
REQUIRED_FILES = [
    ("README.md", "安装与使用说明"),
    ("SKILL.md", "技能主入口"),
    ("references/00-guide-full.md", "v2.0 指引全文"),
    ("references/01-core-workflow.md", "七步 SOP"),
    ("references/02-read-four-questions.md", "读数四问"),
    ("references/03-logic-matrix.md", "三维矩阵"),
    ("references/04-semantic-json.md", "L2 语义 JSON"),
    ("references/05-expectation-layer.md", "预期层"),
    ("references/06-indicator-dictionary.md", "指标字典"),
    ("references/07-pitfalls.md", "误区库"),
    ("references/08-integration.md", "集成协议"),
    ("references/books/_MIRROR_INDEX.md", "书库镜像索引"),
    ("references/books/_inbox/README.md", "投喂区占位（保证空目录进分发包）"),
    ("assets/interpretation_card.md", "解读卡模板（双层契约 v2.3 · 外源检索闭环）"),
    ("assets/golden_set.jsonl", "自测集"),
    # vizmath 内联副本（公式 + 图表出口）
    ("scripts/vizmath/README.md", "vizmath 说明"),
    ("scripts/vizmath/svg_chart.py", "图表出口（零依赖 SVG，默认）"),
    ("scripts/vizmath/tex2omml.py", "公式出口 pandoc→OMML"),
    ("scripts/vizmath/render_figure.py", "图表出口 SV Nature 样式"),
    ("scripts/vizmath/refs/pandoc-omml.md", "公式管线与踩坑"),
    ("scripts/vizmath/refs/journal-figures.md", "图表管线与踩坑"),
    ("scripts/vizmath/_vendor/scientific-visualization/scripts/style_presets.py", "SV 样式（内联）"),
    ("scripts/vizmath/_vendor/scientific-visualization/scripts/figure_export.py", "SV 导出（内联）"),
    ("scripts/vizmath/_vendor/scientific-visualization/scripts/_common.py", "SV 公共库（内联）"),
    ("scripts/vizmath/_vendor/scientific-visualization/assets/color_palettes.py", "SV 调色板（内联）"),
    ("scripts/_vendor/ima_api.cjs", "ima 投喂通道（内联）"),
    ("scripts/check.py", "校验脚本"),
    ("scripts/card_preview.py", "双层卡 → 单页折叠 HTML 预览（零依赖）"),
    ("scripts/ingest_books.py", "书库投喂脚本"),
]
REQUIRED_DIRS = [
    ("references/books/_inbox", "投喂预留区"),
    ("assets/cases", "五领域案例库"),
]


def assetcheck():
    """自足性校验：所有配套资产必须在技能目录内，不得指向技能外的路径。"""
    checks = []
    miss = [f for f, _ in REQUIRED_FILES if not os.path.isfile(os.path.join(SKILL_DIR, f))]
    checks.append({"id": "A1", "name": "核心文件齐备（%d 项）" % len(REQUIRED_FILES),
                   "status": "PASS" if not miss else "FAIL",
                   "detail": "全部齐备" if not miss else "缺失: %s" % miss})
    dmiss = [d for d, _ in REQUIRED_DIRS if not os.path.isdir(os.path.join(SKILL_DIR, d))]
    checks.append({"id": "A2", "name": "目录齐备（%d 项）" % len(REQUIRED_DIRS),
                   "status": "PASS" if not dmiss else "FAIL",
                   "detail": "全部齐备" if not dmiss else "缺失: %s" % dmiss})

    # 外部路径泄漏扫描：技能文档层不得引用技能目录之外的资产
    # 扫描范围 = SKILL.md + README.md + references/** + assets/**（脚本层允许回退分支，不在此列）
    leaks = []
    for base in ("references", "assets"):
        for root, _, files in os.walk(os.path.join(SKILL_DIR, base)):
            if "_vendor" in root:
                continue
            for fn in files:
                if not fn.endswith((".md", ".py")):
                    continue
                p = os.path.join(root, fn)
                try:
                    t = open(p, encoding="utf-8").read()
                except Exception:
                    continue
                for pat in ("_shared/vizmath", ".workbuddy/skills/scientific-visualization",
                            ".workbuddy/skills/ima-skill"):
                    if pat in t:
                        leaks.append("%s: %s" % (os.path.relpath(p, SKILL_DIR), pat))
    for fn in ("SKILL.md", "README.md"):
        p = os.path.join(SKILL_DIR, fn)
        if os.path.isfile(p):
            t = open(p, encoding="utf-8").read()
            for pat in ("_shared/vizmath", ".workbuddy/skills/scientific-visualization",
                        ".workbuddy/skills/ima-skill"):
                if pat in t:
                    leaks.append("%s: %s" % (fn, pat))
    checks.append({"id": "A3", "name": "文档层无技能外资产引用",
                   "status": "PASS" if not leaks else "FAIL",
                   "detail": "干净（扫描 SKILL.md/README.md/references/assets）"
                             if not leaks else "泄漏: %s" % leaks})

    # 可选依赖探测（不算 FAIL，仅提示）
    opt = []
    try:
        import matplotlib  # noqa: F401
        opt.append("matplotlib ✔")
    except Exception:
        opt.append("matplotlib ✘（图表出口需装）")
    try:
        import docx  # noqa: F401
        opt.append("python-docx ✔")
    except Exception:
        opt.append("python-docx ✘（docx 交付需装）")
    sys.path.insert(0, os.path.join(SKILL_DIR, "scripts", "vizmath"))
    try:
        from tex2omml import pandoc_path  # noqa: F401
        pandoc_path()
        opt.append("pandoc ✔")
    except Exception:
        opt.append("pandoc ✘（公式出口需装 pypandoc-binary）")
    import shutil
    opt.append("node %s" % ("✔" if shutil.which("node") else "✘（ima 投喂需装）"))
    checks.append({"id": "A4", "name": "可选依赖探测", "status": "PASS",
                   "detail": " | ".join(opt)})
    return checks


def source_traceability(p1_lines):
    """H6 硬阻断：结论层用到的外源信源标记 T1–T4，必须**同行**可追溯到发布时点。

    判据（机械）：剔除符号表后，**表格行**凡出现 T1–T4 标记，同行必须含日期
    （YYYY-MM / YYYY-MM-DD / YYYY年M月 等）。无日期 = 读者无法判断 as-of，
    也就无法判断该不该参与判定——这直接击穿 v2.3 的截止线机制，故为硬阻断。

    只查表格行的原因：结论层的外源引用必然落在表格里（§2 信源列、§3 表 A/B、
    未获源表、口径三角表）；说明性文字中"J3 用的是 T1 信源"属**泛指提及**，
    不是引用，若一并检查会把解释性文字误判为硬阻断。
    """
    outside = SYMBOL_BLOCK_RE.sub("", "\n".join(p1_lines))
    lines = outside.splitlines()
    tbl = [(i, l) for i, l in enumerate(lines) if l.strip().startswith("|")]
    bad = [i + 1 for i, l in tbl if T_BADGE_RE.search(l) and not DATE_RE.search(l)]
    n_ref = len([1 for _, l in tbl if T_BADGE_RE.search(l)])
    if not n_ref:
        return {"id": "H6", "name": "外源信源可追溯（T 级须配发布时点）", "status": "PASS",
                "detail": "结论层未引用外源信源（自算卡，不适用）"}
    if bad:
        return {"id": "H6", "name": "外源信源可追溯（T 级须配发布时点）", "status": "FAIL",
                "detail": "共 %d 处 T 级标记，其中第 %s 行缺发布时点——读者无从判断 as-of"
                          % (n_ref, "、".join(str(x) for x in bad[:6]))}
    return {"id": "H6", "name": "外源信源可追溯（T 级须配发布时点）", "status": "PASS",
            "detail": "%d 处 T 级标记均可同行追溯到发布时点" % n_ref}


def check_card(text):
    low = text.lower()
    results = []
    # 结构字段（软提示，不计入 H）
    missing_fields = [f for f in FIELDS if f.lower() not in low]
    for hid, (name, groups) in RULES.items():
        ok = all(any(k.lower() in low for k in g) for g in groups)
        detail = "全部命中" if ok else "缺失: " + "; ".join(
            "/".join(g) for g in groups if not any(k.lower() in low for k in g))
        results.append({"id": hid, "name": name, "status": "PASS" if ok else "FAIL", "detail": detail})
    return results, missing_fields


def check_brief(text):
    """v2.4 快读卡契约 B1–B5（第三形态，WARN 级）。

    快读卡**不含**判定清单与外源表 A/B——审计完整性由**回链 + 本校验集**承载。
      B1 首屏存在：标题为「快读卡」且有核心数字区（30 秒可读）
      B2 误读警示在首屏：易误读点必须前置（不得藏进附录）
      B3 时效轴存在：发布 / 事件 / 下一步 在时间轴里
      B4 图必配数表 + alt 文本非空（图片失效时卡片仍可读）
      B5 审计锚点回链 + 符号自解释（无裸符号：正文用到的符号族须在符号表内）
    """
    lines = text.splitlines()
    n = len(lines)
    imgs = [(i, l) for i, l in enumerate(lines) if re.match(r"!\[.*\]\(", l.strip())]
    checks = []

    # --- B1 首屏存在
    has_h1 = any(re.match(r"^#\s*快读卡", l) for l in lines)
    has_core = any(re.search(r"核心数字|一句话结论", l) for l in lines)
    has_tbl = any(l.strip().startswith("|") for l in lines[:FIRST_SCREEN_LINES])
    p1 = []
    if not has_h1:
        p1.append("标题不是「快读卡」（快读卡须自解释自己是哪一层）")
    if not has_core:
        p1.append("缺核心数字 / 一句话结论区——普通读者 30 秒内拿不到读数")
    if not has_tbl:
        p1.append("首屏无读数表")
    checks.append({"id": "B1", "name": "快读卡首屏存在（标题 + 核心数字 + 读数表）",
                   "status": "WARN" if p1 else "PASS",
                   "detail": "; ".join(p1) if p1 else "标题/核心数字/读数表齐备"})

    # --- B2 误读警示在首屏（只看 VISUAL 区块内）
    vis = VISUAL_BLOCK_RE.search(text)
    vtxt = vis.group(1) if vis else text
    p2 = []
    if "⚠" not in vtxt and "不能读成" not in vtxt:
        p2.append("误读警示不在首屏（易误读点必须前置）")
    if "下一步" not in vtxt:
        p2.append("「下一步看什么」不在首屏")
    checks.append({"id": "B2", "name": "误读警示与下一步在首屏",
                   "status": "WARN" if p2 else "PASS",
                   "detail": "; ".join(p2) if p2 else "误读警示 + 下一步均在 VISUAL 区块内"})

    # --- B3 时效轴存在
    has_tl = any(("时效轴" in l or "timeline" in l.lower()) for l in lines)
    has_next = any("下一步" in l for l in lines)
    p3 = []
    if not has_tl:
        p3.append("缺时效轴（发布 → 事件 → 下一步）")
    if not has_next:
        p3.append("缺「下一步看什么」")
    checks.append({"id": "B3", "name": "时效轴存在（发布·事件·下一步）",
                   "status": "WARN" if p3 else "PASS",
                   "detail": "; ".join(p3) if p3 else "时效轴 + 下一步齐备"})

    # --- B4 图必配数表 + alt 文本
    bad_alt, orphan = [], []
    for i, l in imgs:
        m = re.match(r"!\[([^\]]*)\]\(([^)]*)\)", l.strip())
        if not m or not m.group(1).strip():
            bad_alt.append("第%d行" % (i + 1))
            continue
        lo, hi = max(0, i - IMG_TABLE_WINDOW), min(n, i + IMG_TABLE_WINDOW + 1)
        if not any(x.strip().startswith("|") for x in lines[lo:hi]):
            orphan.append("第%d行" % (i + 1))
    p4 = []
    if bad_alt:
        p4.append("图缺 alt 文本: %s" % ",".join(bad_alt))
    if orphan:
        p4.append("孤图（±%d 行内无数表）: %s" % (IMG_TABLE_WINDOW, ",".join(orphan)))
    checks.append({"id": "B4", "name": "图必配数表 + alt 文本",
                   "status": "WARN" if p4 else "PASS",
                   "detail": "图 %d 张，全部 alt 文本 + 邻近数表齐备" % len(imgs)
                             if not p4 else "; ".join(p4)})

    # --- B5 审计锚点回链 + 符号自解释
    p5 = []
    if "审计锚点" not in text:
        p5.append("缺「审计锚点」回链表——快读卡不含判定与信源台账，须显式回链主卡/附录")
    if not re.search(r"\[主卡\]\(.*\.md\)", text):
        p5.append("未回链主卡（结论层）")
    if not re.search(r"\[附录[^\]]*\]\(.*_appendix\.md\)", text):
        p5.append("未回链附录（审计底本）")
    m = SYMBOL_BLOCK_RE.search(text)
    if not m:
        p5.append("缺 <!-- SYMBOLS --> 符号表")
    else:
        outside = SYMBOL_BLOCK_RE.sub("", text)
        undef = [fam for fam, use_rx, def_rx in SYMBOL_FAMILIES + EXTRA_TOKENS
                 if use_rx.search(outside) and not def_rx.search(m.group(1))]
        if undef:
            p5.append("用到但未定义的符号: %s" % "、".join(undef))
        if LEGACY_SCENARIO_RE.search(outside):
            p5.append("情景编号仍用 S-A/B/C，须改 SC-1/2/3")
    checks.append({"id": "B5", "name": "审计锚点回链 + 符号自解释",
                   "status": "WARN" if p5 else "PASS",
                   "detail": "; ".join(p5) if p5 else "审计锚点回链齐备，无裸符号"})

    return checks


def selftest():
    checks = []
    if not os.path.exists(GOLDEN):
        return [{"id": "G0", "name": "golden_set.jsonl 存在", "status": "FAIL", "detail": "文件缺失"}]
    rows = []
    with open(GOLDEN, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    pos = [r for r in rows if r.get("type") == "positive"]
    neg = [r for r in rows if r.get("type") == "negative"]
    checks.append({"id": "G1", "name": "正例 10 条", "status": "PASS" if len(pos) == 10 else "FAIL",
                   "detail": "实到 %d" % len(pos)})
    checks.append({"id": "G2", "name": "负例 10 条", "status": "PASS" if len(neg) == 10 else "FAIL",
                   "detail": "实到 %d" % len(neg)})
    need = {"id", "type", "input", "expect_action", "must_contain", "must_not_contain"}
    bad = [r.get("id", "?") for r in rows if not need.issubset(set(r.keys()))]
    checks.append({"id": "G3", "name": "字段齐全", "status": "PASS" if not bad else "FAIL",
                   "detail": "缺字段: %s" % bad if bad else "全部齐全"})
    allow = {"interpret", "redirect", "refuse"}
    badact = [r.get("id", "?") for r in rows if r.get("expect_action") not in allow]
    checks.append({"id": "G4", "name": "expect_action 合法", "status": "PASS" if not badact else "FAIL",
                   "detail": "非法: %s" % badact if badact else "全部合法"})

    want = {"production": 2, "demand": 2, "prices": 2, "finance": 2, "fiscal": 2}
    for dom, n in want.items():
        p = os.path.join(CASES, "%s.md" % dom)
        if not os.path.exists(p):
            checks.append({"id": "C-" + dom, "name": "案例文件 %s" % dom, "status": "FAIL", "detail": "缺失"})
            continue
        cnt = open(p, encoding="utf-8").read().count("## 案例")
        checks.append({"id": "C-" + dom, "name": "案例 %s × %d" % (dom, n),
                       "status": "PASS" if cnt == n else "FAIL", "detail": "实到 %d" % cnt})

    # v2.4 第三形态：快读卡必须覆盖全部 5 张（五领域教学案例，构造示例）
    want_brief = {"demand", "production", "prices", "finance", "fiscal"}
    missb = sorted(s for s in want_brief
                   if not os.path.isfile(os.path.join(CASES, "%s_brief.md" % s)))
    checks.append({"id": "C-brief", "name": "快读卡 × %d（第三形态全覆盖）" % len(want_brief),
                   "status": "PASS" if not missb else "FAIL",
                   "detail": "全部齐备（教学 5）" if not missb else "缺失: %s" % missb})
    return checks


def main():
    ap = argparse.ArgumentParser(description="econ-indicator-reader 校验")
    ap.add_argument("file", nargs="?", help="解读卡 md（主卡）")
    ap.add_argument("file2", nargs="?", help="附录 md（可选，缺省时自动发现 <stem>_appendix.md）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--assets", action="store_true")
    args = ap.parse_args()

    if args.assets:
        checks = assetcheck()
        if args.json:
            print(json.dumps({"checks": checks}, ensure_ascii=False, indent=1))
        else:
            for c in checks:
                print("[%s] %s — %s (%s)" % (c["status"], c["id"], c["name"], c["detail"]))
        return 0 if all(c["status"] == "PASS" for c in checks) else 1

    if args.selftest:
        checks = selftest()
        if args.json:
            print(json.dumps({"checks": checks}, ensure_ascii=False, indent=1))
        else:
            for c in checks:
                print("[%s] %s — %s (%s)" % (c["status"], c["id"], c["name"], c["detail"]))
        return 0 if all(c["status"] == "PASS" for c in checks) else 1

    if not args.file or not os.path.exists(args.file):
        print("用法: python scripts/check.py <解读卡.md> [--json] | --selftest")
        return 2

    _base = os.path.basename(args.file)
    _stem = os.path.splitext(_base)[0]

    main_text = open(args.file, encoding="utf-8").read()

    # v2.4 快读卡（第三形态）：只跑 B1–B5 快读卡契约，不跑双层 H/V
    if _stem.endswith("_brief"):
        bres = check_brief(main_text)
        _bwarns = [c["id"] for c in bres if c["status"] != "PASS"]
        _payload = {
            "file": args.file, "kind": "brief", "checks": bres,
            "warns": _bwarns,
            "pass": all(c["status"] == "PASS" for c in bres),
            "next_actions": [
                "【须主动询问用户，不得静默等待触发】是否生成单页折叠 HTML 预览"
                "（首屏直呈 / 图表内联 / 符号末尾折叠）："
                "python scripts/card_preview.py %s -o %s.html [--dark]" % (_base, _stem),
                "快读卡 WARN（%s）交付前须消除或书面说明理由" % (", ".join(_bwarns) or "无"),
                "本卡不含判定与信源台账：完整审计见主卡 + 附录（回链表见「审计锚点」）",
            ],
        }
        if args.json:
            print(json.dumps(_payload, ensure_ascii=False, indent=1))
        else:
            print("校验: %s  （快读卡契约 · 第三形态）" % args.file)
            print("  --- 快读卡契约 B1–B5 ---")
            for c in bres:
                print("  [%s] %s %s — %s" % (c["status"], c["id"], c["name"], c["detail"]))
            if _payload["warns"]:
                print("结论: %d 条 WARN（%s）— 交付前须消除或书面说明理由"
                      % (len(_payload["warns"]), ", ".join(_payload["warns"])))
            else:
                print("结论: 全部通过")
            print("  --- 交付下一步（第 1 项须主动询问用户，不得静默）---")
            for k, a in enumerate(_payload["next_actions"], 1):
                print("  %d) %s" % (k, a))
        return 0 if _payload["pass"] else 1

    # 双层契约：合并主卡 + 附录后按整篇校验 H1–H5，再对 Part 1 做结构层 V1–V12
    app_path = args.file2 if args.file2 and os.path.isfile(args.file2) else discover_appendix(args.file)
    app_text = open(app_path, encoding="utf-8").read() if app_path else None
    full_text = main_text + (("\n" + app_text) if app_text else "")

    results, missing_fields = check_card(full_text)
    p1_lines, _, _layered_ignored = split_parts(main_text, app_text)
    results.append(source_traceability(p1_lines))     # H6 只看结论层
    structs, layered = structure_checks(main_text, app_text)
    p1_low = "\n".join(p1_lines).lower()
    missing_p1 = [f for f in PART1_FIELDS if f.lower() not in p1_low]
    warns = [s["id"] for s in structs if s["status"] != "PASS"]
    payload = {
        "file": args.file,
        "appendix": app_path,
        "checks": results,
        "structure": structs,
        "missing_fields": missing_fields,
        "missing_part1_fields": missing_p1,
        "layered": layered,
        "hard_pass": all(r["status"] == "PASS" for r in results),
        "warns": warns,
        "pass": all(r["status"] == "PASS" for r in results),
        "next_actions": [
            "【须主动询问用户，不得静默等待触发】是否生成单页折叠 HTML 预览"
            "（Part1 直呈 / Part2 折叠 / 依据锚点可点击 / 图片内联）："
            "python scripts/card_preview.py %s -o %s.html [--dark] [--open-appendix]"
            % (_base, _stem),
            "结构层 WARN（%s）交付前须消除或书面说明理由" % (", ".join(warns) or "无"),
            "交付时提醒用户本卡的失效时点（见卡内「时效」行）",
        ],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
    else:
        print("校验: %s%s" % (args.file,
                             ("  + 附录 %s" % os.path.basename(app_path)) if app_path else "  (未发现附录)"))
        print("  --- 硬阻断 H1–H6 ---")
        for r in results:
            print("  [%s] %s %s — %s" % (r["status"], r["id"], r["name"], r["detail"]))
        print("  --- 结构层 V1–V12 ---")
        for s in structs:
            print("  [%s] %s %s — %s" % (s["status"], s["id"], s["name"], s["detail"]))
        if missing_fields:
            print("  [提示] 缺八字段: %s" % ", ".join(missing_fields))
        if payload["missing_part1_fields"]:
            print("  [提示] Part 1 结论层缺锚点: %s" % ", ".join(payload["missing_part1_fields"]))
        if not layered:
            print("  [提示] 单层卡形态：建议拆为「主卡 + _appendix.md」双层（见模板 v2.0）")
        if payload["warns"]:
            print("结论: 硬阻断全过，但结构层 %d 条 WARN（%s）— 交付前须消除或书面说明理由"
                  % (len(payload["warns"]), ", ".join(payload["warns"])))
        elif payload["pass"]:
            print("结论: 全部通过")
        else:
            print("结论: 存在硬阻断，不得输出终稿")
        if payload["pass"]:
            print("  --- 交付下一步（第 1 项须主动询问用户，不得静默）---")
            for k, a in enumerate(payload["next_actions"], 1):
                print("  %d) %s" % (k, a))
    return 0 if payload["pass"] else 1


def discover_appendix(main_path):
    """双层契约：自动发现同名 `<stem>_appendix.md` 兄弟文件。"""
    stem, ext = os.path.splitext(main_path)
    cand = stem + "_appendix" + ext
    return cand if os.path.isfile(cand) else None


def split_parts(main_text, appendix_text=None):
    """切出 Part 1（结论层）与 Part 2（附录层）。返回 (p1_lines, p2_lines, 是否已分层)。"""
    lines = main_text.splitlines()
    app = appendix_text.splitlines() if appendix_text is not None else None
    end1 = [i for i, l in enumerate(lines) if "/PART1:CONCLUSION" in l]
    p2 = [i for i, l in enumerate(lines) if "PART2:APPENDIX" in l]
    if end1:
        p1 = lines[:end1[0]]
    elif p2:
        p1 = lines[:p2[0]]
    else:
        p1 = lines
    if app is not None:
        p2l = app
    elif p2:
        p2l = lines[p2[0]:]
    else:
        p2l = []
    layered = bool(end1 or p2 or app is not None)
    return p1, p2l, layered


def _section(lines, *titles):
    """取某节的行列表：从命中任一 title 的标题行起，到下一个 '## ' 标题止。"""
    start = None
    for i, l in enumerate(lines):
        if l.strip().startswith("#") and any(t in l for t in titles):
            start = i
            break
    if start is None:
        return [], None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].strip().startswith("## "):
            end = j
            break
    return lines[start:end], start


def structure_checks(main_text, appendix_text=None):
    """双层契约结构层校验 V1–V8。全部为 WARN 级（不改退出码，交付前须消除或说明理由）。"""
    p1, p2, layered = split_parts(main_text, appendix_text)
    full = main_text.splitlines() + (appendix_text.splitlines() if appendix_text else [])
    total = max(len([l for l in full if l.strip()]), 1)
    checks = []

    # --- S1 双层分层存在
    has_p1_mark = any("PART1:CONCLUSION" in l for l in main_text.splitlines())
    if layered or has_p1_mark:
        st, d = "PASS", "双层已分离（Part1 %d 行 / Part2 %d 行）" % (len(p1), len(p2))
    else:
        st, d = "WARN", "未见双层标记且无附录文件——仍是单层卡（旧形态）"
    checks.append({"id": "V1", "name": "双层契约分层", "status": st, "detail": d})

    # --- S2 结论前置与主次占比
    idx_heads = [(i, l) for i, l in enumerate(full) if re.match(r"^#{1,3}\s", l)]
    first_concl = next((i for i, l in idx_heads
                        if re.search(r"^\s*(##\s*)?1\s*[\.、]?\s*(分层)?结论", l)), None)
    p2_start = next((i for i, l in enumerate(full) if "PART2:APPENDIX" in l), None)
    if p2_start is None and p2:
        p2_start = len(p1)
    n_p1 = len([l for l in p1 if l.strip()])
    n_total = len([l for l in (p1 + p2) if l.strip()]) or 1
    ratio = n_p1 / n_total
    ok_pre = (p2_start is None) or (first_concl is not None and first_concl < p2_start)
    if ratio <= MAX_PART1_RATIO and ok_pre:
        st = "PASS"
    elif ratio > MAX_PART1_RATIO:
        st = "WARN"
    else:
        st = "WARN"
    # first_concl 可能为 None（无「1 分层结论」标题），须先判空再加一
    d = "结论层占比 %.0f%%（红线 %d%%）｜结论位置 %s" % (
        ratio * 100, MAX_PART1_RATIO * 100,
        ("第 %s 行，在附录之前 OK" % (first_concl + 1 if first_concl is not None else 0))
        if ok_pre else "未在附录之前 ✘")
    if ratio > MAX_PART1_RATIO:
        d += " → 结论层膨胀，应下沉内容到附录"
    checks.append({"id": "V2", "name": "结论前置与主次占比", "status": st, "detail": d})

    # --- S3/S4/S5 判定清单
    sec, s_start = _section(p1, "判定清单", "2 判定清单")
    rows = [l for l in sec if l.strip().startswith("|")]
    body, header = [], None
    for r in rows:
        cells = [c.strip() for c in r.strip().strip("|").split("|")]
        joined = "".join(cells)
        if set(joined) <= set("-: "):
            continue                      # 分隔行
        # 表头 = 该表的**第一行**（v2.3 起列数可变，须按表头定位列）。
        # 不可用"cells[0] 含'判定'"来识别——判定正文里也常出现"判定"二字，会把数据行误当表头。
        if header is None:
            header = cells
            continue
        body.append((r, cells))

    n_j = len(body)
    st = "PASS" if n_j <= MAX_JUDGMENTS else "WARN"
    d = "判定条目 %d 条（上限 %d）" % (n_j, MAX_JUDGMENTS)
    if n_j > MAX_JUDGMENTS:
        d += " → 超限，须合并或下沉到附录"
    if n_j == 0:
        st = "WARN"
        d += "（未识别到判定条目，检查是否用了 | # | 判定 | 置信等级 | 推翻条件 | 依据 | 表头）"
    checks.append({"id": "V3", "name": "判定条目上限 ≤%d" % MAX_JUDGMENTS,
                   "status": st, "detail": d})

    st = "PASS" if len(sec) <= MAX_LISTING_LINES else "WARN"
    d = "清单区 %d 行（上限 %d）" % (len(sec), MAX_LISTING_LINES)
    if len(sec) > MAX_LISTING_LINES:
        d += " → 结论区二次膨胀，须精简"
    checks.append({"id": "V4", "name": "判定清单区 ≤%d 行" % MAX_LISTING_LINES,
                   "status": st, "detail": d})

    def _col(cells, keys, default=""):
        """按表头定位列（v2.3 起判定清单列数可变，不得硬编码列位）。"""
        if header:
            for i, c in enumerate(header):
                if any(k in c for k in keys):
                    return cells[i] if i < len(cells) else default
        return default

    bad_t, bad_a, bad_conf, bad_src = [], [], [], []
    for r, cells in body:
        label = cells[0].strip("* ") if cells else "?"
        if len(cells) < 5:
            bad_t.append(label); bad_a.append(label); bad_conf.append(label)
            continue
        # 表头优先；无表头时按 v2.3 六列 / v2.0 五列回退（找含 →§ 的列为锚点）
        refute = _col(cells, ("推翻",), cells[3] if len(cells) > 3 else "")
        anchor = _col(cells, ("依据", "锚点"),
                      cells[4] if len(cells) > 4 else "")
        conf = _col(cells, ("置信", "三分"), cells[2] if len(cells) > 2 else "")
        src = _col(cells, ("信源",), None)
        if "→" not in anchor and len(cells) > 4:      # 回退：扫描含 →§ 的列
            anchor = next((c for c in cells if "→" in c and "§" in c), anchor)
        if refute in ("", "—", "-", "同上"):
            bad_t.append(label)
        if "→" not in anchor or "§" not in anchor:
            bad_a.append(label)
        if not any(k in conf for k in ("已知事实", "合理推论", "待验证假设")):
            bad_conf.append(label)
        # v2.3：信源列须填（T级×独立源数，或自算填 —）
        if src is not None and not src.strip():
            bad_src.append(label)
    probs = []
    if bad_t:
        probs.append("推翻条件缺失/占位: %s" % ",".join(bad_t))
    if bad_a:
        probs.append("依据锚点非 [→§X] 格式: %s" % ",".join(bad_a))
    if bad_conf:
        probs.append("置信等级未用三分法: %s" % ",".join(bad_conf))
    if bad_src:
        probs.append("信源列为空（v2.3 须填 T级×独立源数，自算填 —）: %s" % ",".join(bad_src))
    checks.append({"id": "V5", "name": "每条判定含三分法+推翻条件+依据锚点",
                   "status": "PASS" if not probs and body else "WARN",
                   "detail": "全部齐备（%d 条）" % len(body) if not probs and body
                             else "; ".join(probs)})

    # --- S6 图必配数表
    imgs = [(i, l) for i, l in enumerate(full) if re.match(r"!\[.*\]\(", l.strip())]
    orphan = []
    for i, l in imgs:
        lo, hi = max(0, i - IMG_TABLE_WINDOW), min(len(full), i + IMG_TABLE_WINDOW + 1)
        if not any(x.strip().startswith("|") for x in full[lo:hi]):
            orphan.append("第%d行" % (i + 1))
    checks.append({"id": "V6", "name": "图必配数表（图片失效时卡片仍可读）",
                   "status": "PASS" if not orphan else "WARN",
                   "detail": "图 %d 张，全部邻近有数表" % len(imgs) if not orphan
                             else "孤图（周围 %d 行内无数表）: %s" % (IMG_TABLE_WINDOW, ", ".join(orphan))})

    # --- S7 补数清单与依据链闭合（附录层）
    has_list = any(re.search(r"\|\s*N\d+\s*\|", l) for l in p2) or "补数清单" in "\n".join(p2)
    has_chain = "依据链" in main_text
    st = "PASS" if (has_list and has_chain) else "WARN"
    d = []
    d.append("补数清单 %s" % ("✔" if has_list else "✘"))
    d.append("依据链 %s" % ("✔" if has_chain else "✘"))
    if not (has_list and has_chain):
        d.append("→ J 编号须能追到 §小节，N 编号须能追到补数清单")
    checks.append({"id": "V7", "name": "补数清单与依据链闭合", "status": st,
                   "detail": " ｜ ".join(d)})

    # --- V8 符号表闭合：结论层的编号/单位/标记必须自解释
    checks.append(symbol_checks(p1))

    # --- V9 外源检索闭环（v2.3）：自主检索 + 信源分级 + as-of 截止线 + 口径三角
    txt_p1 = "\n".join(p1)
    out_sym = SYMBOL_BLOCK_RE.sub("", txt_p1)
    probs = []
    # 只看**剔除符号表后**的正文：符号表里会提到"§3 外源印证"，那是索引不是内容
    if not re.search(r"^#{2,4}\s*\d*\s*外源印证", out_sym, re.M):
        probs.append("缺 §3 外源印证区——P0 补数项与共识项须自主检索并标注信源分级")
    n_ids = sorted(set(re.findall(r"(?<![A-Za-z0-9])N(\d+)", out_sym)))
    sec1, _ = _section(p1, "分层结论", "1 分层结论")
    n_status = len([l for l in sec1 if any(m in l for m in STATUS_MARKS)])
    if n_ids and n_status < len(n_ids):
        probs.append("N 项 %s 共 %d 个，仅 %d 处标了检索状态（✅ 已补 / ⚠ 未获合格信源 / ○ 未检索）"
                     % ("、".join("N" + i for i in n_ids), len(n_ids), n_status))
    # 单文件形态（Part1/Part2 标记内联同一文件）也要能看到附录区——split_parts 已把
    # PART2:APPENDIX 之后的行归入 p2，双文件形态下 p2 即附录正文，故两者同源。
    app_txt = "\n".join(p2)
    # 须是**小节标题**，不能只是正文提到 §K（附录头部的指引文字也会提到）
    if not re.search(r"^#{2,4}\s*§K", app_txt, re.M):
        probs.append("附录缺 §K 外源检索日志（§K1 执行记录 / §K2 信源清单 / §K3 口径三角 / §K4 未获源记录）")
    if "口径三角" not in out_sym and "口径三角" not in app_txt:
        probs.append("缺口径三角表——跨口径对比必须先做口径对齐，不得直接比数值")
    checks.append({"id": "V9", "name": "外源检索闭环（自主检索 + 信源分级 + 截止线）",
                   "status": "WARN" if probs else "PASS",
                   "detail": "; ".join(probs) if probs else
                   "§3 外源印证齐备｜%d 个 N 项已标检索状态｜附录 §K 检索日志 + 口径三角齐备" % len(n_ids)})

    # --- V10 首屏可读性契约（v2.4）：普通读者 30 秒内须拿到「读数 / 对照 / 差距 / 误读警示 / 下一步」
    first = p1[:FIRST_SCREEN_LINES]
    ftxt = "\n".join(first)
    miss10 = []
    if not any(l.strip().startswith("|") for l in first):
        miss10.append("首屏无核心读数表（普通读者拿不到「读数 vs 对照 vs 差距」）")
    if "⚠" not in ftxt and "不能读成" not in ftxt:
        miss10.append("误读警示不在首屏（易误读点必须前置）")
    if "下一步" not in ftxt and "时效" not in ftxt:
        miss10.append("「下一步看什么 / 时效」不在首屏")
    checks.append({"id": "V10", "name": "首屏可读性契约（读数·对照·差距·误读警示·下一步）",
                   "status": "WARN" if miss10 else "PASS",
                   "detail": "; ".join(miss10) if miss10
                             else "首屏含核心读数表 + 误读警示 + 下一步/时效"})

    # --- V11 折叠契约（v2.4）：**审计型**专业大表不得挤占首屏，须下沉或折叠。
    # 只列审计台账特征（表 A/B、口径三角、未获源）；判定清单是结论层**主体**，
    # 其规模已由 V3（≤5 条）/ V4（≤20 行）约束，不在此列——否则等于要求结论层无判定。
    PROF_HEADS = ("口径三角", "参与判定", "未获合格信源", "后续进展", "表 A", "表 B")
    prof = [(i + 1) for i, l in enumerate(p1[:FIRST_SCREEN_LINES])
            if l.strip().startswith("|") and any(k in l for k in PROF_HEADS)]
    checks.append({"id": "V11", "name": "折叠契约（专业大表不占首屏）",
                   "status": "WARN" if prof else "PASS",
                   "detail": "首屏无专业大表（判定清单/表A/B/口径三角均已后置）"
                             if not prof else "首屏第 %s 行出现专业表头，应下沉或折叠"
                                              % "、".join(str(x) for x in prof[:6])})

    # --- V12 视觉契约（v2.4）：**结论层**图须 alt 文本 + 数表 + 「读图：」一句 + 来源/as-of/T级
    # 只查结论层（p1）的图：附录是审计底本，其配图已由 V6「图必配数表」约束，
    # 再让它也满足首屏式读图/来源标注会把审计过程图挤成装饰。
    bad_alt, bad_cap = [], []
    for i, l in imgs:
        if i >= len(p1):
            continue
        m = re.match(r"!\[([^\]]*)\]\(([^)]*)\)", l.strip())
        if not m or not m.group(1).strip():
            bad_alt.append("第%d行" % (i + 1))
            continue
        lo, hi = max(0, i - IMG_TABLE_WINDOW), min(len(full), i + IMG_TABLE_WINDOW + 1)
        win = full[lo:hi]
        if not any("读图" in x for x in win):
            bad_cap.append("第%d行缺「读图：」一句" % (i + 1))
        if not any(("as-of" in x or "T级" in x or T_BADGE_RE.search(x)) for x in win):
            bad_cap.append("第%d行图注缺来源/as-of/T级" % (i + 1))
    _p = bad_alt + bad_cap
    checks.append({"id": "V12", "name": "视觉契约（图 alt+数表+读图一句+来源/T级）",
                   "status": "WARN" if _p else "PASS",
                   "detail": "图 %d 张，全部 alt 文本+数表+读图+来源齐备" % len(imgs)
                             if not _p else "; ".join(_p)})

    return checks, layered


def symbol_checks(p1):
    """V8：结论层符号自解释。

    三条机械判据：
      ① 存在 <!-- SYMBOLS:START/END --> 符号表，且**置于结论层末尾作待查项**
         （v2.2 起：若挤在判定清单之前即 WARN——它会占掉首屏，违背"结论主导"）；
      ② 结论层用到的每个符号族/单位/标记，符号表内都有定义行（used ⊆ defined）；
      ③ 未出现已被废止的 S-A/B/C 情景编号（与结构校验 V1–V8 撞名）。
    """
    txt = "\n".join(p1)
    m = SYMBOL_BLOCK_RE.search(txt)
    if not m:
        return {"id": "V8", "name": "符号表闭合（结论层符号自解释）", "status": "WARN",
                "detail": "缺 <!-- SYMBOLS:START/END --> 符号表——读者无从得知 J1 / SC-1 / N1 / §D / pp 的含义"}

    table = m.group(1)
    # 使用检测只看符号表**之外**的正文：表内自述的废止编号不算在用
    outside = SYMBOL_BLOCK_RE.sub("", txt)
    probs = []

    # ① 位置：须在结论层末尾（v2.2：不得挤在判定清单之前占首屏）
    sym_line = txt[:m.start()].count("\n")
    _, j_start = _section(p1, "判定清单", "2 判定清单")
    if j_start is not None and sym_line < j_start:
        probs.append("符号表在第%d行，早于判定清单（第%d行）——应移到结论层末尾作待查项，"
                     "不得占用首屏" % (sym_line + 1, j_start + 1))

    # ② used ⊆ defined
    undef = [fam for fam, use_rx, def_rx in SYMBOL_FAMILIES + EXTRA_TOKENS
             if use_rx.search(outside) and not def_rx.search(table)]
    if undef:
        probs.append("用到但未定义: %s" % "、".join(undef))

    # ③ 废止编号（只看正文，符号表内的"已废止"说明不算）
    if LEGACY_SCENARIO_RE.search(outside):
        probs.append("情景编号仍用 S-A/B/C，与结构校验 V1–V8 撞名，须改 SC-1/2/3")

    n_def = len([l for l in table.splitlines() if l.strip().startswith("|")]) - 2
    detail = "符号表已登记 %d 项，位置第%d行（结论层末尾·待查项 OK）" % (max(n_def, 0), sym_line + 1)
    if probs:
        detail = "; ".join(probs)
    return {"id": "V8", "name": "符号表闭合（结论层符号自解释）",
            "status": "WARN" if probs else "PASS", "detail": detail}


if __name__ == "__main__":
    sys.exit(main())
