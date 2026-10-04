#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
svg_chart.py —— econ-indicator-reader 的**零依赖**图表出口。

与 render_figure.py（matplotlib / Nature 样式 / PDF+PNG）的分工：
  - 本模块：纯标准库，无需安装任何包，**永远可用**；输出 SVG（矢量），
    供解读卡默认消费（md/HTML 内嵌或外链）。
  - render_figure.py：需 matplotlib；用于投稿/打印级 PDF+PNG。
  -> 默认走本模块；只有需要高质量出版时回退到 render_figure.py。

配色约定：**涨红跌绿**（中国惯例），货币符号 ¥。
色板取 Okabe-Ito 色盲安全色，light/dark 双主题。

用法:
    import sys; sys.path.insert(0, "<skill>/scripts/vizmath")
    from svg_chart import diverging_bar, waterfall, dual_track, path_line, save

    svg = diverging_bar(
        items=[("总PCE同比", 3.40), ("核心PCE同比", 3.00)],
        baseline=2.0, baseline_label="美联储 2% 目标",
        title="通胀距政策目标缺口（pp）", unit="pp", theme="light")
    save(svg, "figure_gap.svg")
"""
import math
import os
import tempfile
import xml.sax.saxutils as su

# ---------------------------------------------------------------- 主题与色板

# Okabe-Ito 色盲安全核心色
OI = {
    "vermillion": "#D55E00",   # 涨 / 高于基准（红）
    "bluish_green": "#009E73",  # 跌 / 低于基准（绿）
    "blue": "#0072B2",
    "orange": "#E69F00",
    "sky": "#56B4E9",
    "purple": "#CC79A7",
    "yellow": "#F0E442",
    "black": "#000000",
}

THEMES = {
    "light": {"bg": "#FFFFFF", "fg": "#1A1A1A", "muted": "#5B6472",
              "grid": "#D8DCE3", "panel": "#F6F8FA", "accent": OI["blue"]},
    "dark": {"bg": "#14181F", "fg": "#E8EAED", "muted": "#9AA3AE",
             "grid": "#333A44", "panel": "#1B212B", "accent": OI["sky"]},
}

FONT = "'PingFang SC','Microsoft YaHei','Noto Sans SC','Segoe UI',Helvetica,Arial,sans-serif"


def _t(name="light"):
    return THEMES.get(name, THEMES["light"])


def _esc(s):
    return su.escape(str(s))


def _fmt(v, unit=""):
    if v is None:
        return "—"
    s = ("%+.*f" % (2, v)) if abs(v) < 1000 else ("%.*f" % (0, v))
    if float(v) == int(v) and abs(v) < 1000 and not str(s).startswith("+"):
        s = "%d" % int(v)
    return s + unit


def _wrap_cn(text, n):
    """按字符数折行（中文无空格，只能按字断）。返回不超过 2 行的片段列表。"""
    lines, cur = [], ""
    for ch in str(text):
        cur += ch
        if len(cur) >= n:
            lines.append(cur)
            cur = ""
    if cur:
        lines.append(cur)
    return lines[:2]


# ---------------------------------------------------------------- 状态色（涨红跌绿 + 中性）

STATE_COLOR = {
    "up": OI["vermillion"],        # 涨 / 高于对照
    "down": OI["bluish_green"],    # 跌 / 低于对照
    "flat": None,                  # 中性，用前景色
    "release": OI["blue"],         # 时间轴：发布
    "event": OI["orange"],         # 时间轴：事件
    "next": OI["purple"],          # 时间轴：下一步
}


# ---------------------------------------------------------------- 通用骨架

def _canvas(width, height, th, title, subtitle=""):
    """返回 (parts, hs)；hs = 内容区起始 y（标题占用后的高度）。"""
    p = []
    p.append('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
             'viewBox="0 0 %d %d" font-family="%s" role="img">'
             % (width, height, width, height, FONT))
    p.append('<rect width="%d" height="%d" fill="%s"/>' % (width, height, th["bg"]))
    hs = 24
    if title:
        hs += 26
        p.append('<text x="%d" y="%d" font-size="15" font-weight="600" fill="%s">%s</text>'
                 % (20, 30, th["fg"], _esc(title)))
    if subtitle:
        hs += 20
        p.append('<text x="%d" y="%d" font-size="11.5" fill="%s">%s</text>'
                 % (20, 30 + 22, th["muted"], _esc(subtitle)))
    return p, hs


def _close(parts):
    parts.append("</svg>")
    return "\n".join(parts)


def save(svg, path):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return path


# ---------------------------------------------------------------- 图一：距基准缺口（水平发散条）

def diverging_bar(items, baseline=0.0, baseline_label="基准", title="", subtitle="",
                  unit="", theme="light", width=680, bar_h=26, gap=14,
                  good_direction="down"):
    """水平发散条：每条以 baseline 为中心向左/向右延伸。

    items          : [(label, value), ...]
    good_direction : "down" 表示低于基准为好（绿），高于为坏（红）；
                     "up"   反之。用于"距目标缺口""距历史均值偏离"等。
    """
    th = _t(theme)
    label_w = 150
    plot_w = width - label_w - 130
    height = 24 + (26 if title else 0) + (20 if subtitle else 0) + \
        len(items) * (bar_h + gap) + 34
    p, hs = _canvas(width, height, th, title, subtitle)

    vals = [v for _, v in items] + [baseline]
    vmax = max(vals)
    vmin = min(vals)
    span = (vmax - vmin) or 1.0
    pad = span * 0.18
    lo, hi = vmin - pad, vmax + pad

    def xpos(v):
        return label_w + (v - lo) / (hi - lo) * plot_w

    x0 = xpos(baseline)

    # 基准竖线
    p.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="1.2" '
             'stroke-dasharray="4,3"/>' % (x0, hs - 6, x0, hs + len(items) * (bar_h + gap) + 4,
                                           th["fg"]))
    p.append('<text x="%.1f" y="%d" font-size="10.5" fill="%s" text-anchor="middle">%s</text>'
             % (x0, hs - 10, th["fg"], _esc(baseline_label)))

    for i, (lab, v) in enumerate(items):
        y = hs + i * (bar_h + gap)
        xv = xpos(v)
        bx, bw = (x0, xv - x0) if v >= baseline else (xv, x0 - xv)
        above = v > baseline
        good = (not above) if good_direction == "down" else above
        col = OI["bluish_green"] if good else OI["vermillion"]
        p.append('<text x="%d" y="%.1f" font-size="12" fill="%s">%s</text>'
                 % (16, y + bar_h * 0.68, th["fg"], _esc(lab)))
        p.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s" rx="2"/>'
                 % (bx, y, max(bw, 1.5), bar_h, col))
        tx = xv + (8 if v >= baseline else -8)
        anc = "start" if v >= baseline else "end"
        p.append('<text x="%.1f" y="%.1f" font-size="12" font-weight="600" fill="%s" '
                 'text-anchor="%s">%s</text>' % (tx, y + bar_h * 0.68, col, anc, _fmt(v, unit)))

    # 说明条
    py = hs + len(items) * (bar_h + gap) + 12
    p.append('<text x="16" y="%d" font-size="10.5" fill="%s">红=偏离不利方向 · 绿=有利方向'
             ' · 虚线=%s(%s)</text>' % (py, th["muted"], _esc(baseline_label), _fmt(baseline, unit)))
    return _close(p)


# ---------------------------------------------------------------- 图二：贡献分解瀑布

def waterfall(start_label, start_value, steps, end_label, title="", subtitle="",
              unit="pp", theme="light", width=680, height=None):
    """瀑布图：从起点逐项累加到终点，正项绿/负项红由"是否推高结果"决定
    （本函数按**数值正负**着色：正=红(涨)，负=绿(跌)，符合涨红跌绿）。"""
    th = _t(theme)
    steps = list(steps)
    total = start_value + sum(d for _, d in steps)
    seq = [(start_label, start_value, "total")] + \
          [(lab, d, "step") for lab, d in steps] + [(end_label, total, "total")]

    allv = [start_value, total]
    run = start_value
    for _, d in steps:
        run += d
        allv.append(run)
    vmax, vmin = max(allv + [0]), min(allv + [0])
    span = (vmax - vmin) or 1.0
    pad = span * 0.15
    lo, hi = vmin - pad, vmax + pad

    top = 24 + (26 if title else 0) + (20 if subtitle else 0)
    left, right = 56, 24
    plot_w = width - left - right
    plot_h = 240 if height is None else height - top - 46
    H = top + plot_h + 46
    p, hs = _canvas(width, H, th, title, subtitle)

    def ypos(v):
        return hs + plot_h - (v - lo) / (hi - lo) * plot_h

    # 网格 + 零线
    for k in range(5):
        gv = lo + (hi - lo) * k / 4.0
        gy = ypos(gv)
        p.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="0.8"/>'
                 % (left, gy, left + plot_w, gy, th["grid"]))
        p.append('<text x="%d" y="%.1f" font-size="10" fill="%s" text-anchor="end">%s</text>'
                 % (left - 6, gy + 3.5, th["muted"], _fmt(gv, unit)))
    if lo < 0 < hi:
        p.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1.2"/>'
                 % (left, ypos(0), left + plot_w, ypos(0), th["fg"]))

    n = len(seq)
    bw = plot_w / n * 0.62
    step = plot_w / n
    run = start_value
    for i, (lab, v, kind) in enumerate(seq):
        cx = left + step * (i + 0.5)
        x = cx - bw / 2
        if kind == "total":
            y0, y1 = ypos(0), ypos(v)
            col = OI["blue"]
            top_y, hgt = min(y0, y1), abs(y1 - y0)
            p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" rx="1.5"/>'
                     % (x, top_y, bw, max(hgt, 1.2), col))
            p.append('<text x="%.1f" y="%.1f" font-size="11.5" font-weight="700" fill="%s" '
                     'text-anchor="middle">%s</text>'
                     % (cx, top_y - 6, col, _fmt(v, unit)))
        else:
            before, run = run, run + v
            yb, ya = ypos(before), ypos(run)
            top_y, hgt = min(yb, ya), abs(ya - yb)
            col = OI["vermillion"] if v >= 0 else OI["bluish_green"]
            p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" rx="1.5"/>'
                     % (x, top_y, bw, max(hgt, 1.2), col))
            p.append('<text x="%.1f" y="%.1f" font-size="11" font-weight="600" fill="%s" '
                     'text-anchor="middle">%s</text>'
                     % (cx, top_y - 6, col, _fmt(v, unit)))
            if i < n - 1:
                p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                         'stroke-width="0.9" stroke-dasharray="3,2"/>'
                         % (x + bw, ya, x + bw + step - bw, ya, th["muted"]))
        # 标签（两行折行避免拥挤）
        words, lines, cur = str(lab), [], ""
        for ch in words:
            cur += ch
            if len(cur) >= 6:
                lines.append(cur)
                cur = ""
        if cur:
            lines.append(cur)
        lines = lines[:2]
        for k, ln in enumerate(lines):
            p.append('<text x="%.1f" y="%.1f" font-size="10" fill="%s" text-anchor="middle">%s</text>'
                     % (cx, hs + plot_h + 16 + k * 12, th["fg"], _esc(ln)))
    return _close(p)


# ---------------------------------------------------------------- 图三：双轨对比（分组条）

def dual_track(items, series_names, title="", subtitle="", unit="%",
               theme="light", width=680, height=None):
    """分组条形：同一组左右两根，用于「同比 vs 环比折年」「名义 vs 实际」等双轨对照。"""
    th = _t(theme)
    left, right = 150, 96
    plot_w = width - left - right
    top = 24 + (26 if title else 0) + (20 if subtitle else 0)
    grp_h = 52
    plot_h = grp_h * len(items)
    H = top + plot_h + 40
    p, hs = _canvas(width, H, th, title, subtitle)

    vals = [v for it in items for v in it[1]]
    vmax, vmin = max(vals + [0]), min(vals + [0])
    span = (vmax - vmin) or 1.0
    lo = vmin - span * 0.15 if vmin < 0 else 0
    hi = vmax + span * 0.15

    def xpos(v):
        return left + (v - lo) / (hi - lo) * plot_w

    xz = xpos(0)
    p.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="1.2"/>'
             % (xz, hs, xz, hs + plot_h, th["fg"]))

    colors = [OI["blue"], OI["orange"], OI["purple"]]
    for i, (lab, vals_i) in enumerate(items):
        gy = hs + i * grp_h
        bh = grp_h * 0.28
        p.append('<text x="%d" y="%.1f" font-size="12" fill="%s">%s</text>'
                 % (16, gy + grp_h * 0.5, th["fg"], _esc(lab)))
        for j, v in enumerate(vals_i):
            by = gy + grp_h * 0.16 + j * (bh + 5)
            bx, bw = (xz, xpos(v) - xz) if v >= 0 else (xpos(v), xz - xpos(v))
            col = colors[j % len(colors)]
            p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" rx="1.5"/>'
                     % (bx, by, max(bw, 1.2), bh, col))
            tx = xpos(v) + (6 if v >= 0 else -6)
            anc = "start" if v >= 0 else "end"
            p.append('<text x="%.1f" y="%.1f" font-size="11" font-weight="600" fill="%s" '
                     'text-anchor="%s">%s</text>' % (tx, by + bh * 0.78, col, anc, _fmt(v, unit)))
    # 图例
    ly = hs + plot_h + 16
    for j, nm in enumerate(series_names):
        p.append('<rect x="%d" y="%d" width="11" height="11" fill="%s" rx="1.5"/>'
                 % (16 + j * 150, ly - 9, colors[j % len(colors)]))
        p.append('<text x="%d" y="%d" font-size="10.5" fill="%s">%s</text>'
                 % (31 + j * 150, ly, th["fg"], _esc(nm)))
    return _close(p)


# ---------------------------------------------------------------- 图四：路径与关键点

def path_line(points, annotations=None, baseline=None, baseline_label="",
              title="", subtitle="", unit="", theme="light", width=680, height=300):
    """折线路径：用于季节性/月度序列、历史轨迹。annotations=[(idx, "text")]。"""
    th = _t(theme)
    left, right, top_pad, bot = 56, 24, 10, 44
    top = 24 + (26 if title else 0) + (20 if subtitle else 0)
    plot_w = width - left - right
    plot_h = height - top - bot
    p, hs = _canvas(width, height, th, title, subtitle)

    xs = [pt[1] for pt in points] + ([baseline] if baseline is not None else [])
    vmax, vmin = max(xs), min(xs)
    span = (vmax - vmin) or 1.0
    lo, hi = vmin - span * 0.15, vmax + span * 0.15

    def X(i):
        return left + (i / max(len(points) - 1, 1)) * plot_w

    def Y(v):
        return hs + top_pad + plot_h - 2 * top_pad - (v - lo) / (hi - lo) * (plot_h - 2 * top_pad)

    for k in range(5):
        gv = lo + (hi - lo) * k / 4.0
        gy = Y(gv)
        p.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="0.8"/>'
                 % (left, gy, left + plot_w, gy, th["grid"]))
        p.append('<text x="%d" y="%.1f" font-size="10" fill="%s" text-anchor="end">%s</text>'
                 % (left - 6, gy + 3.5, th["muted"], _fmt(gv, unit)))

    if baseline is not None:
        gy = Y(baseline)
        p.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1.1" '
                 'stroke-dasharray="4,3"/>' % (left, gy, left + plot_w, gy, OI["bluish_green"]))
        if baseline_label:
            p.append('<text x="%d" y="%.1f" font-size="10" fill="%s">%s</text>'
                     % (left + 4, gy - 5, OI["bluish_green"], _esc(baseline_label)))

    d = " ".join("%s%.1f,%.1f" % ("M" if i == 0 else "L", X(i), Y(v))
                 for i, (_, v) in enumerate(points))
    p.append('<path d="%s" fill="none" stroke="%s" stroke-width="2"/>' % (d, th["accent"]))
    for i, (_, v) in enumerate(points):
        p.append('<circle cx="%.1f" cy="%.1f" r="3" fill="%s" stroke="%s" stroke-width="1.2"/>'
                 % (X(i), Y(v), th["bg"], th["accent"]))

    step_lab = max(1, math.ceil(len(points) / 10.0))
    for i, (lab, _) in enumerate(points):
        if i % step_lab == 0 or i == len(points) - 1:
            p.append('<text x="%.1f" y="%d" font-size="9.5" fill="%s" text-anchor="middle">%s</text>'
                     % (X(i), hs + plot_h + 16, th["muted"], _esc(lab)))

    for idx, txt in (annotations or []):
        if 0 <= idx < len(points):
            _, v = points[idx]
            p.append('<text x="%.1f" y="%.1f" font-size="10" fill="%s" text-anchor="middle">%s</text>'
                     % (X(idx), Y(v) - 10, OI["vermillion"], _esc(txt)))
    return _close(p)


# ---------------------------------------------------------------- 图五：首屏数字卡

def stat_cards(cards, title="", subtitle="", theme="light", width=680, cols=3):
    """首屏核心读数卡（**快读卡专用首屏件**）。

    cards : [(label, value, note, state), ...]
            label   —— 指标名（如「总 PCE 同比」）
            value   —— **已格式化好的字符串**（允许 “+1.1%” “3.40%” “—”）
            note    —— 一行对照/补充（如「目标 2.0% · 差 +1.40pp」），可空
            state   —— "up"（涨红）/ "down"（跌绿）/ "flat" 或 None（中性）
    cols   : 每行几张卡；实际列数取 min(cols, len(cards))。

    **颜色不单独承载信息**：state 只决定数字颜色，label 与 note 始终有文字。
    """
    th = _t(theme)
    cards = list(cards)
    if not cards:
        raise ValueError("stat_cards: cards 为空")
    cols = max(1, min(cols, len(cards)))
    rows = math.ceil(len(cards) / cols)
    pad_x, gap_x, gap_y, card_h = 20, 12, 10, 96
    card_w = (width - pad_x * 2 - gap_x * (cols - 1)) / cols
    top = 24 + (26 if title else 0) + (20 if subtitle else 0)
    H = top + rows * card_h + (rows - 1) * gap_y + 30
    p, hs = _canvas(width, H, th, title, subtitle)

    for i, (lab, val, note, state) in enumerate(cards):
        r, c = divmod(i, cols)
        x = pad_x + c * (card_w + gap_x)
        y = hs + r * (card_h + gap_y)
        col = STATE_COLOR.get(state, None) or th["fg"]
        p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%d" fill="%s" rx="6" '
                 'stroke="%s" stroke-width="1"/>'
                 % (x, y, card_w, card_h, th["panel"], th["grid"]))
        p.append('<text x="%.1f" y="%.1f" font-size="11.5" fill="%s">%s</text>'
                 % (x + 12, y + 22, th["muted"], _esc(lab)))
        p.append('<text x="%.1f" y="%.1f" font-size="23" font-weight="700" fill="%s">%s</text>'
                 % (x + 12, y + 56, col, _esc(val)))
        if note:
            for k, ln in enumerate(_wrap_cn(note, 16)):
                p.append('<text x="%.1f" y="%.1f" font-size="10.5" fill="%s">%s</text>'
                         % (x + 12, y + 76 + k * 13, th["muted"], _esc(ln)))
    p.append('<text x="%d" y="%d" font-size="10.5" fill="%s">红=高于对照 · 绿=低于对照'
             ' · 卡片仅给读数，判定见主卡</text>' % (pad_x, H - 10, th["muted"]))
    return _close(p)


# ---------------------------------------------------------------- 图六：时效时间轴

def timeline(events, title="", subtitle="", theme="light", width=680):
    """首屏时效轴：发布 → 事件 → 下一步。

    events : [(date, text, kind), ...]
            kind ∈ "release"（发布）/ "event"（事件）/ "next"（下一步）/ 其他（中性）
    圆点颜色 + **文字前缀**（发布 / 事件 / 下一步）双重编码，色盲可读。
    """
    th = _t(theme)
    events = list(events)
    if not events:
        raise ValueError("timeline: events 为空")
    row_h, date_w, dot_x = 46, 96, 20 + 96 + 16
    top = 24 + (26 if title else 0) + (20 if subtitle else 0)
    H = top + len(events) * row_h + 30
    p, hs = _canvas(width, H, th, title, subtitle)

    ax_y0, ax_y1 = hs + 10, hs + len(events) * row_h - 10
    p.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1.4"/>'
             % (dot_x, ax_y0, dot_x, ax_y1, th["grid"]))

    PREFIX = {"release": "发布", "event": "事件", "next": "下一步"}
    for i, (date, text, kind) in enumerate(events):
        y = hs + i * row_h
        cy = y + row_h * 0.34
        col = STATE_COLOR.get(kind, th["fg"])
        p.append('<circle cx="%d" cy="%.1f" r="4.5" fill="%s" stroke="%s" stroke-width="1.5"/>'
                 % (dot_x, cy, th["bg"], col))
        p.append('<circle cx="%d" cy="%.1f" r="2.6" fill="%s"/>' % (dot_x, cy, col))
        p.append('<text x="%d" y="%.1f" font-size="11" font-weight="600" fill="%s">%s</text>'
                 % (20, cy + 4, th["fg"], _esc(date)))
        p.append('<text x="%d" y="%.1f" font-size="10" fill="%s">%s</text>'
                 % (dot_x + 14, cy - 6, col, _esc(PREFIX.get(kind, ""))))
        for k, ln in enumerate(_wrap_cn("%s · %s" % (PREFIX.get(kind, ""), text), 30)):
            p.append('<text x="%d" y="%.1f" font-size="11.5" fill="%s">%s</text>'
                     % (dot_x + 14, cy + 9 + k * 15, th["fg"], _esc(ln)))
    p.append('<text x="%d" y="%d" font-size="10.5" fill="%s">虚线轴仅示次序 · 事件口径见附录 §K</text>'
             % (20, H - 10, th["muted"]))
    return _close(p)


# ---------------------------------------------------------------- 图七：四闸门灯

def gate_lights(gates, title="", subtitle="", theme="light", width=680):
    """verdict 四闸门指示灯。

    gates : [(name, status, note), ...]
            status ∈ "pass"（实线绿·✓）/ "partial"（虚线橙·?，**未校准警示**）/
                     "fail"（红·✗）/ "na"（灰·○，不适用）
    状态**永远**以 ✓ / ? / ✗ / ○ 文字 + 边框虚实双重编码，不靠颜色单打独斗。
    """
    th = _t(theme)
    gates = list(gates)
    if not gates:
        raise ValueError("gate_lights: gates 为空")
    pad_x, gap_x, card_h = 20, 12, 78
    n = len(gates)
    card_w = (width - pad_x * 2 - gap_x * (n - 1)) / n
    top = 24 + (26 if title else 0) + (20 if subtitle else 0)
    H = top + card_h + 30
    p, hs = _canvas(width, H, th, title, subtitle)

    META = {
        "pass":    (OI["bluish_green"], "solid",   "✓", "通过"),
        "partial": (OI["orange"],       "dashed",  "?", "未校准"),
        "fail":    (OI["vermillion"],   "solid",   "✗", "未过"),
        "na":      (th["muted"],        "dashed",  "○", "不适用"),
    }
    for i, (name, status, note) in enumerate(gates):
        x = pad_x + i * (card_w + gap_x)
        col, dash, mark, word = META.get(status, META["na"])
        p.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s" rx="6" stroke="%s" '
                 'stroke-width="1.5" %s/>'
                 % (x, hs, card_w, card_h, th["panel"], col,
                    "" if dash == "solid" else 'stroke-dasharray="5,3"'))
        p.append('<circle cx="%.1f" cy="%d" r="9" fill="%s" stroke="%s" stroke-width="1.5" %s/>'
                 % (x + 26, hs + 28, th["bg"], col,
                    "" if dash == "solid" else 'stroke-dasharray="4,2"'))
        p.append('<text x="%.1f" y="%d" font-size="12" font-weight="700" fill="%s" '
                 'text-anchor="middle">%s</text>' % (x + 26, hs + 33, col, mark))
        p.append('<text x="%.1f" y="%d" font-size="11.5" fill="%s">%s</text>'
                 % (x + 44, hs + 24, th["fg"], _esc(name)))
        p.append('<text x="%.1f" y="%d" font-size="11" fill="%s">%s</text>'
                 % (x + 44, hs + 40, col, _esc(word)))
        for k, ln in enumerate(_wrap_cn(note or "", 10)):
            p.append('<text x="%.1f" y="%d" font-size="10" fill="%s">%s</text>'
                     % (x + 12, hs + 62 + k * 12, th["muted"], _esc(ln)))
    p.append('<text x="%d" y="%d" font-size="10.5" fill="%s">虚线框 = 未校准，不得当概率用'
             ' · 判定见主卡 §6</text>' % (pad_x, H - 10, th["muted"]))
    return _close(p)


# ---------------------------------------------------------------- 自检

def _selftest(out_dir=None):
    # 默认落临时目录：自检示例图属过程产物，不得污染技能目录（历史教训：曾生成 `_fig_out/`）
    out_dir = out_dir or os.path.join(tempfile.gettempdir(), "econ_ind_svg_selftest")
    os.makedirs(out_dir, exist_ok=True)
    made = []
    made.append(save(diverging_bar([("总PCE同比", 3.40), ("核心PCE同比", 3.00)],
                                   baseline=2.0, baseline_label="2% 目标", unit="pp",
                                   good_direction="down",
                                   title="距政策目标缺口（示例）", theme="light"),
                     os.path.join(out_dir, "demo_gap.svg")))
    made.append(save(waterfall("8月同比基准", 1.10, [("汽车类", -1.29), ("石油类", -0.20),
                                                     ("其他净贡献", 0.49)],
                               "除汽车后", title="贡献分解（示例）", unit="pp"),
                     os.path.join(out_dir, "demo_waterfall.svg")))
    made.append(save(dual_track([("总PCE", (3.40, 3.82)), ("核心PCE", (3.00, 3.09))],
                                ["同比（已实现）", "环比折年（动能）"],
                                title="水平 vs 动能（示例）", unit="%"),
                     os.path.join(out_dir, "demo_dual.svg")))
    made.append(save(path_line([("1月", 0.21), ("2月", 0.27), ("3月", 0.12), ("4月", -0.23),
                                ("5月", -0.10), ("6月", 0.40), ("7月", 0.01), ("8月", -0.13)],
                               annotations=[(5, "6月高点")], unit="%",
                               title="季调环比路径（示例）"),
                     os.path.join(out_dir, "demo_path.svg")))
    made.append(save(stat_cards(
        [("总 PCE 同比", "3.40%", "目标 2.0% · 差 +1.40pp", "up"),
         ("核心 PCE 同比", "3.00%", "目标 2.0% · 差 +1.00pp", "up"),
         ("surprise", "−0.30pp", "共识 3.30% · 换尺子 −0.29pp", "down")],
        title="30 秒数字卡（示例）", subtitle="as-of 2026-09-30 · T2×3", theme="light"),
        os.path.join(out_dir, "demo_stat_cards.svg")))
    made.append(save(timeline(
        [("2026-09-30", "8月 PCE 发布 + 方法修订", "release"),
         ("2026-10-01", "政策路径定价冲突", "event"),
         ("2026-10-29", "9月 PCE · 10月 FOMC", "next")],
        title="时效轴（示例）", theme="light"),
        os.path.join(out_dir, "demo_timeline.svg")))
    made.append(save(gate_lights(
        [("A 口径", "pass", "新旧口径"),
         ("B 一致性", "pass", "双轨闭合"),
         ("C 交叉验证", "partial", "待 BEA 一手"),
         ("D 预期", "pass", "共识已补")],
        title="四闸门（示例）", theme="light"),
        os.path.join(out_dir, "demo_gate_lights.svg")))
    made.append(save(gate_lights([("D 预期", "partial", "未校准")], theme="dark",
                                  title="未校准闸门必须用虚线框（示例）"),
                     os.path.join(out_dir, "demo_gate_dark.svg")))
    # 校验三函数均抛错保护
    for fn, kw in ((stat_cards, {"cards": []}), (timeline, {"events": []}),
                   (gate_lights, {"gates": []})):
        try:
            fn(**kw)
        except ValueError:
            pass
        else:
            raise SystemExit("selftest: %s 空输入未抛 ValueError" % fn.__name__)
    bad = [p for p in made if not os.path.isfile(p)]
    return 1 if bad else 0


if __name__ == "__main__":
    import sys
    # 用法：python svg_chart.py [输出目录]
    # 注意：`-h` / `--help` 会被 argparse 风格调用（如 --assets 里的探测），
    # 必须过滤掉，否则会被当成目录名建出 `--help/` 之类的垃圾目录。
    _args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if len(sys.argv) > 1 and not _args:
        print("用法：python svg_chart.py [输出目录]   # 省略则自检到临时目录，不污染技能目录")
        raise SystemExit(0)
    sys.exit(_selftest(_args[0]) if _args else _selftest())
