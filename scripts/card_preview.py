#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
card_preview.py —— 双层解读卡的**单页自包含 HTML 预览**出口（零依赖，纯标准库）。

解决什么问题：
    双层契约把过程下沉到附录后，附录若只是一个独立 md 文件，"按需展开"就退化成
    "换一个文件继续读"。本脚本把 Part 1 与 Part 2 合成**一个 HTML**：
      · Part 1 结论层  —— 直接呈现，占首屏
      · Part 2 附录层  —— 按 § 小节折叠进 <details>，默认收起
      · 依据锚点 [→§X] —— 渲染为可点击跳转链接（这是追溯性的关键闭环）
      · 信源分级 T1–T4 —— 渲染为徽章，悬停显示该级可依赖性（T1 官方一手 → T4 未交叉验证）
      · 符号表         —— `<!-- SYMBOLS -->` 块抽为末尾折叠盒子（**默认收起**，id=symbol-table，
                          字号小于正文；正文编号 chip 点击时自动展开并跳转）
      · 编号 chip      —— 正文里的 J1 / SC-1 / N1 / §D 包成 chip，悬停显示含义、点击跳回符号表
      · 图片           —— SVG 内联、位图转 base64 data URI，产物**离线可用**

    python scripts/card_preview.py <主卡.md> [-o 输出.html] [--open-appendix] [--dark]
    python scripts/card_preview.py <主卡.md> <附录.md>
    python scripts/card_preview.py <快读卡.md> [-o 输出.html] [--dark]

新增 v2.4 第三形态「快读卡」（<stem>_brief.md）预览：
    快读卡是给普通用户看的三件套首屏，与「主卡 / 附录」是并列的两条腿，不是层级包含。
      · VISUAL 区块（<!-- VISUAL:START --> …）→ **直接呈现**，占首屏，不折叠
      · 审计锚点 / 免责 → 首屏之后同一页直呈（都是两行，藏起来反而看不见）
      · 符号表 `<!-- SYMBOLS -->` → 末尾 `<details>` 折叠盒，**默认收起**（id=symbol-table）
      · 顶栏回链 → 跳回同目录 [主卡.md] / [附录.md]

说明：省略附录文件时，自动发现同名 `<stem>_appendix.md`。
"""
import argparse
import base64
import html
import os
import re
import sys

HEADINGS_RE = re.compile(r"^(#{1,6})\s+(.*)$")
SEC_RE = re.compile(r"^(§)([A-K])(\.?\d+)?")
# 符号表块（结论层，机器可解析）
SYM_BLOCK_RE = re.compile(r"<!--\s*/?\s*SYMBOLS:START\s*-->(.*?)<!--\s*/?\s*SYMBOLS:END\s*-->", re.S)
# v2.4 快读卡首屏契约区：<!-- VISUAL:START --> … <!-- /VISUAL:END -->
VISUAL_BLOCK_RE = re.compile(r"<!--\s*VISUAL:START\s*-->(.*?)<!--\s*/VISUAL:END\s*-->", re.S)
# 编号 chip：正文里每出现一次就包一层，悬停显示含义、点击跳回符号表
SYM_TITLES = [
    (re.compile(r"(?<![A-Za-z0-9])J(\d+)"),
     "判定条目 J{0}（J = Judgment）：判定清单第 {0} 条，必带「置信等级 + 推翻条件 + 依据锚点」三件套"),
    (re.compile(r"(?<![A-Za-z0-9])SC-(\d+)"),
     "情景 SC-{0}（SC = Scenario Case）：条件式推演分支，不是预测"),
    (re.compile(r"(?<![A-Za-z0-9])N(\d+)"),
     "补数项 N{0}（N = Needed data）：把判定推到可支撑还缺的第 {0} 个数"),
    (re.compile(r"§([A-K](?:\.\d+)?)"),
     "附录 §{0} 小节：本判定的依据落点，可点击跳转展开"),
]

# 信源分级徽章（v2.3）：T1 官方一手 → T4 未交叉验证
T_TITLES = {
    "1": "信源 T1 · 官方一手：发布机构原始稿（如 BEA / 国家统计局 / 中汽协官网）",
    "2": "信源 T2 · 官方授权或权威机构：通讯社调查、监管/学术机构（如 Reuters、LSEG、Cleveland Fed）",
    "3": "信源 T3 · 主流媒体或专业数据库：内容可靠但非一手，须交叉验证",
    "4": "信源 T4 · 自媒体或未交叉验证：仅作线索，不得单独支撑判定",
}
T_BADGE_RE = re.compile(r"(?<![A-Za-z0-9])T([1-4])(?![0-9])")


def _sym_wrap(t):
    """把 J1 / SC-1 / N1 / §D 包成带悬浮注解的 chip（结论层面向大众读者的自解释）。"""
    for rx, tmpl in SYM_TITLES:
        t = rx.sub(lambda m: '<a class="sym" href="#symbol-table" title="%s">%s</a>'
                             % (html.escape(tmpl.format(m.group(1))), m.group(0)), t)
    return t


def _tbadge_wrap(t):
    """把 T1–T4 包成信源分级徽章（悬停显示该级的含义与可依赖性）。"""
    return T_BADGE_RE.sub(
        lambda m: '<span class="tbadge t%s" title="%s">T%s</span>'
                  % (m.group(1), html.escape(T_TITLES[m.group(1)]), m.group(1)), t)

CSS = """
:root{
  --bg:#ffffff; --fg:#1a1a1a; --muted:#5b6472; --line:#d8dce3; --panel:#f6f8fa;
  --accent:#0072b2; --up:#d55e00; --down:#009e73; --code:#0b3d62;
}
*{box-sizing:border-box}
body{margin:0;padding:0;background:var(--bg);color:var(--fg);
     font-family:'PingFang SC','Microsoft YaHei','Noto Sans SC','Segoe UI',Helvetica,Arial,sans-serif;
     font-size:15px;line-height:1.75}
.wrap{max-width:900px;margin:0 auto;padding:28px 22px 96px}
.bar{position:sticky;top:0;z-index:9;background:var(--bg);border-bottom:1px solid var(--line);
     padding:10px 0;margin-bottom:18px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.bar .title{font-weight:600;font-size:13.5px;color:var(--muted);margin-right:auto}
.bar button{font:inherit;font-size:12.5px;padding:5px 11px;border:1px solid var(--line);
     background:var(--panel);color:var(--fg);border-radius:5px;cursor:pointer}
.bar button:hover{border-color:var(--accent);color:var(--accent)}
h1{font-size:24px;border-bottom:2px solid var(--fg);padding-bottom:10px;margin:0 0 6px}
h2{font-size:19px;margin:30px 0 12px;padding-left:10px;border-left:4px solid var(--accent)}
h3{font-size:16px;margin:22px 0 10px;color:var(--accent)}
h4{font-size:14.5px;margin:18px 0 8px;color:var(--muted)}
blockquote{margin:12px 0;padding:10px 14px;background:var(--panel);border-left:3px solid var(--line);
     color:var(--muted);font-size:13.5px;border-radius:0 4px 4px 0}
blockquote a{color:var(--accent)}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:13.5px}
th,td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
th{background:var(--panel);font-weight:600}
tbody tr:nth-child(even){background:rgba(0,0,0,.015)}
figure{margin:16px 0;padding:14px;background:var(--panel);border:1px solid var(--line);border-radius:6px}
figure svg,figure img{width:100%;height:auto;display:block;background:#fff;border-radius:4px}
figcaption{margin-top:8px;font-size:12.5px;color:var(--muted);text-align:center}
pre{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:12px 14px;overflow:auto}
pre.tex{font-family:'Cambria Math','Times New Roman',serif;font-size:14.5px;text-align:center}
pre.code{font-family:'Cascadia Mono',Consolas,'Courier New',monospace;font-size:12.5px}
code{background:var(--panel);padding:1px 5px;border-radius:3px;font-size:13px}
hr{border:0;border-top:1px solid var(--line);margin:26px 0}
p{margin:10px 0}
a{color:var(--accent)}
a.anchor{display:inline-block;min-width:52px;padding:1px 7px;border:1px solid var(--accent);
   border-radius:11px;font-size:11.5px;text-decoration:none;white-space:nowrap}
a.anchor:hover{background:var(--accent);color:#fff}
/* 快读卡（v2.4 第三形态）专用 */
.bar a.blink{font-size:12.5px;padding:4px 10px;border:1px solid var(--accent);border-radius:5px;
     text-decoration:none;background:var(--panel);white-space:nowrap}
.bar a.blink:hover{background:var(--accent);color:#fff}
.lead{margin:0 0 18px;padding:9px 13px;border:1px dashed var(--line);border-radius:6px;
     font-size:12.5px;color:var(--muted);background:var(--panel)}
.onepager{margin-bottom:8px}
ul,ol{margin:10px 0 10px 22px;padding:0}
li{margin:4px 0}
/* 附录折叠区 */
.appendix{margin-top:34px;border-top:2px solid var(--fg);padding-top:8px}
.appendix > h1{font-size:20px;border:0}
details{border:1px solid var(--line);border-radius:6px;margin:10px 0;background:var(--bg)}
details[open]{background:var(--panel)}
summary{cursor:pointer;padding:11px 14px;font-weight:600;font-size:14.5px;list-style:none;
        display:flex;align-items:center;gap:8px}
summary::-webkit-details-marker{display:none}
summary::before{content:"▸";color:var(--accent);font-size:13px;transition:transform .15s}
details[open] summary::before{transform:rotate(90deg)}
summary:hover{color:var(--accent)}
details .body{padding:2px 16px 14px;border-top:1px solid var(--line)}
details .body > *:first-child{margin-top:12px}
:target{animation:flash 1.6s ease-out}
@keyframes flash{0%{background:#fff3cd}100%{background:transparent}}
.tag{display:inline-block;font-size:11.5px;padding:1px 8px;border-radius:10px;
     border:1px solid var(--line);color:var(--muted);background:var(--panel)}
/* 符号表盒子（结论层末尾·待查项：默认收起，字号明显小于正文） */
.sym-box{border:1px dashed var(--line);border-radius:8px;background:var(--panel);
     margin:26px 0 10px;font-size:11.5px;color:var(--muted)}
.sym-box>summary{cursor:pointer;padding:7px 12px;font-weight:500;font-size:12.5px;
     list-style:none;display:flex;align-items:center;gap:8px;color:var(--muted)}
.sym-box[open]>summary{border-bottom:1px solid var(--line);color:var(--fg)}
.sym-box>summary::-webkit-details-marker{display:none}
.sym-box>summary::before{content:"▸";color:var(--accent);font-size:11px;transition:transform .15s}
.sym-box[open]>summary::before{transform:rotate(90deg)}
.sym-box .body{padding:6px 12px 12px}
.sym-box blockquote{font-size:11.5px;margin:6px 0;padding:6px 10px}
.sym-box table{font-size:11px;margin:6px 0;line-height:1.55}
.sym-box th,.sym-box td{padding:4px 7px}
.sym-box th{white-space:nowrap;font-weight:600}
/* 编号 chip：悬停显示含义，点击跳回符号表 */
a.sym{display:inline-block;font-family:'Cascadia Mono',Consolas,'Courier New',monospace;
     font-size:.88em;padding:0 4px;margin:0 1px;border:1px solid var(--line);border-radius:4px;
     background:var(--bg);color:inherit;text-decoration:none;cursor:help;white-space:nowrap}
a.sym:hover{border-color:var(--accent);color:var(--accent)}
/* 信源分级徽章 T1–T4：由强到弱，T4 为警示色 */
.tbadge{display:inline-block;font-family:'Cascadia Mono',Consolas,'Courier New',monospace;
     font-size:.78em;font-weight:600;padding:0 5px;margin:0 1px;border-radius:3px;
     border:1px solid transparent;cursor:help;white-space:nowrap;vertical-align:1px}
.tbadge.t1{background:#0b3d62;color:#fff;border-color:#0b3d62}
.tbadge.t2{background:#0072b2;color:#fff;border-color:#0072b2}
.tbadge.t3{background:var(--panel);color:var(--muted);border-color:var(--line)}
.tbadge.t4{background:#fff3cd;color:#8a5a00;border-color:#e0c98a}
@media print{.bar{display:none}details{border:0}details .body{display:block}}
"""

DARK_OVERRIDE = """
:root{--bg:#14181f;--fg:#e8eaed;--muted:#9aa3ae;--line:#333a44;--panel:#1b212b;
      --accent:#56b4e9;--up:#e69f00;--down:#009e73;}
a{color:var(--accent)} tbody tr:nth-child(even){background:rgba(255,255,255,.03)}
figure svg,figure img{background:#fff}
"""

JS = """
document.addEventListener('click', function(e){
  const t = e.target.closest('a.anchor');
  if(!t) return;
  const el = document.getElementById(t.getAttribute('href').slice(1));
  if(!el) return;
  /* 逐级展开所有祖先 <details>：目标可能是三级标题（如 §K3），
     只展开它自己不够，必须把外层折叠块一起打开才看得见 */
  for(var p = el; p; p = p.parentElement){
    if(p.tagName === 'DETAILS'){ p.open = true; }
  }
});
/* 正文编号 chip（J1 / SC-1 / N1 / §D）→ 自动展开符号表并跳过去 */
document.addEventListener('click', function(e){
  const s = e.target.closest('a.sym');
  if(!s) return;
  const d = document.getElementById('symbol-table');
  if(d && d.tagName === 'DETAILS'){ d.open = true; }
});
if(location.hash === '#symbol-table'){
  const d = document.getElementById('symbol-table');
  if(d) d.open = true;
}
/* 顶栏按钮：快读卡预览里按钮可能不存在（本页没有折叠附录），故一律做空值保护 */
function on(id, fn){ var e = document.getElementById(id); if(e) e.addEventListener('click', fn); }
on('btn-open', function(){
  document.querySelectorAll('details').forEach(function(d){ d.open = true; });
});
on('btn-close', function(){
  document.querySelectorAll('details').forEach(function(d){ d.open = false; });
});
on('btn-top', function(){
  window.scrollTo({top:0, behavior:'smooth'});
});
on('btn-expand', function(){
  var d = document.getElementById('symbol-table');
  if(d){ d.open = true; d.scrollIntoView({behavior:'smooth', block:'center'}); }
});
"""


# ---------------------------------------------------------------- 工具

def _slug(text):
    """从 '§D · S4 双轨解码' / '§D.1 分项拉动表' / '§K3 口径三角' 生成 id 片段 D / D1 / K3。"""
    m = SEC_RE.match(text.strip())
    if not m:
        return re.sub(r"[^\w\u4e00-\u9fa5]+", "-", text)[:24]
    return m.group(2) + (re.sub(r"\D", "", m.group(3)) if m.group(3) else "")


def _embed(rel, base_dir):
    """把图片内联：SVG 直接嵌源码，位图转 base64；找不到就原样退化为外链。"""
    path = os.path.normpath(os.path.join(base_dir, rel))
    if not os.path.isfile(path):
        return rel
    try:
        raw = open(path, "rb").read()
    except Exception:
        return rel
    if rel.lower().endswith(".svg"):
        try:
            return "@@INLINE@@" + raw.decode("utf-8")
        except UnicodeDecodeError:
            return rel
    ext = os.path.splitext(rel)[1].lstrip(".").lower() or "png"
    return "data:image/%s;base64,%s" % (ext, base64.b64encode(raw).decode("ascii"))


def inline_md(t, base_dir):
    """行内 Markdown → HTML（含 [→§X] 锚点与图片内联）。"""
    # 先保护图片
    imgs = []

    def _stash(m):
        alt, src = m.group(1), m.group(2)
        imgs.append((alt, _embed(src, base_dir)))
        return "\x00IMG%d\x00" % (len(imgs) - 1)

    t = re.sub(r"!\[(.+?)\]\((.+?)\)", _stash, t)
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    # [→§X] 锚点先占位，避免 chip 的 title 把 § 吞掉后锚点正则失配
    anchors = []

    def _stash_anchor(m):
        anchors.append(m.group(1))
        return "\x00ANC%d\x00" % (len(anchors) - 1)

    t = re.sub(r"\[→§([A-K](?:\.?\d+)?)\]", _stash_anchor, t)
    t = _sym_wrap(t)                      # 编号 chip：悬停显示含义、点击跳回符号表
    t = _tbadge_wrap(t)                   # 信源分级徽章 T1–T4：悬停显示该级可依赖性
    for i, sid in enumerate(anchors):     # 还原为可点击跳转锚点
        t = t.replace("\x00ANC%d\x00" % i,
                      '<a class="anchor" href="#sec-%s">→§%s</a>' % (sid.replace(".", ""), sid))
    t = re.sub(r"\[(.+?)\]\((?!#)(.+?)\)", r'<a href="\2">\1</a>', t)
    for i, (alt, src) in enumerate(imgs):
        mark = "\x00IMG%d\x00" % i
        alt_h = html.escape(alt)
        if src.startswith("@@INLINE@@"):          # SVG：内联源码，离线可用
            frag = '<figure>%s<figcaption>%s</figcaption></figure>' % (
                src[len("@@INLINE@@"):], alt_h)
        elif src.startswith("data:"):              # 位图：base64 data URI
            frag = '<figure><img src="%s" alt="%s"><figcaption>%s</figcaption></figure>' % (
                src, alt_h, alt_h)
        else:                                      # 找不到文件：退化为外链
            frag = '<figure><img src="%s" alt="%s"><figcaption>%s</figcaption></figure>' % (
                html.escape(src), alt_h, alt_h)
        t = t.replace(mark, frag)
    return t


# ---------------------------------------------------------------- 渲染

def render_block(lines, i, base_dir):
    """处理一行，返回 (html片段, 新的i)。表格/代码块/标题/引用/列表/段落。"""
    s = lines[i].strip()

    if s.startswith("```"):
        lang = s[3:].strip()
        buf, i = [], i + 1
        while i < len(lines) and not lines[i].strip().startswith("```"):
            buf.append(lines[i])
            i += 1
        cls = "code"
        return '<pre class="%s">%s</pre>' % (cls, html.escape("\n".join(buf))), i + 1

    if s.startswith("$$"):
        # 单行 $$...$$：必须单独处理，否则会吞掉后续全部正文
        if len(s) > 4 and s.endswith("$$"):
            return '<pre class="tex">%s</pre>' % html.escape(s), i + 1
        buf, i = [s], i + 1
        while i < len(lines) and not lines[i].strip().endswith("$$"):
            buf.append(lines[i])
            i += 1
            if i >= len(lines):               # 未闭合保护，避免吞掉全文
                break
        if i < len(lines):
            buf.append(lines[i])
        return '<pre class="tex">%s</pre>' % html.escape("\n".join(buf)), i + 1

    m = HEADINGS_RE.match(s)
    if m:
        lvl, txt = len(m.group(1)), m.group(2)
        body = inline_md(txt, base_dir)
        sid = _slug(txt) if SEC_RE.match(txt.strip()) else ""
        idattr = ' id="sec-%s"' % sid if sid else ""
        return "<h%d%s>%s</h%d>" % (lvl, idattr, body, lvl), i + 1

    if s.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].strip()) <= set("|-: "):
        rows, j = [], i
        while j < len(lines) and lines[j].strip().startswith("|"):
            rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
            j += 1
        head, body_rows = rows[0], rows[2:]
        th = "".join("<th>%s</th>" % inline_md(c, base_dir) for c in head)
        tb = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % inline_md(c, base_dir) for c in r)
                     for r in body_rows)
        return ("<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (th, tb), j)

    if s.startswith(">"):
        buf = []
        while i < len(lines) and lines[i].strip().startswith(">"):
            buf.append(lines[i].strip().lstrip(">").strip())
            i += 1
        return "<blockquote>%s</blockquote>" % inline_md(" ".join(buf), base_dir), i

    if s.startswith("---") and set(s) <= set("-"):
        return "<hr>", i + 1

    if re.match(r"^([-*]|\d+\.)\s+", s):
        buf, ordered = [], bool(re.match(r"^\d+\.", s))
        while i < len(lines) and re.match(r"^([-*]|\d+\.)\s+", lines[i].strip()):
            buf.append(re.sub(r"^([-*]|\d+\.)\s+", "", lines[i].strip()))
            i += 1
        tag = "ol" if ordered else "ul"
        items = "".join("<li>%s</li>" % inline_md(x, base_dir) for x in buf)
        return "<%s>%s</%s>" % (tag, items, tag), i

    buf = []
    while i < len(lines) and lines[i].strip() and not (
            lines[i].strip().startswith(("#", ">", "|", "```", "$$", "---")) or
            re.match(r"^([-*]|\d+\.)\s+", lines[i].strip())):
        buf.append(lines[i].strip())
        i += 1
    return "<p>%s</p>" % inline_md(" ".join(buf), base_dir), i


def render_md(text, base_dir):
    """Markdown 文本 → HTML 片段。"""
    lines = [l for l in text.splitlines() if not l.strip().startswith("<!--")]
    out, i = [], 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        frag, i = render_block(lines, i, base_dir)
        out.append(frag)
    return "\n".join(out)


def split_parts(main_text):
    """按标记切 Part 1 / Part 2；同一文件内也可分离。"""
    ls = main_text.splitlines()
    end1 = next((k for k, l in enumerate(ls) if "/PART1:CONCLUSION" in l), None)
    st2 = next((k for k, l in enumerate(ls) if "PART2:APPENDIX" in l), None)
    if end1:
        p1 = ls[:end1]
        p2 = ls[st2:] if st2 else []
    elif st2:
        p1, p2 = ls[:st2], ls[st2:]
    else:
        p1, p2 = ls, []
    return "\n".join(p1), "\n".join(p2)


def build_html(main_text, appendix_text, base_dir, open_all=False, dark=False, links=()):
    """主卡（两层契约）→ 单页自包含 HTML。

    `links` 为三件套回链 chip（附录 / 快读卡）：主卡页也要能一键跳走，
    否则读者只会陷入审计底本里出不来（v2.4 双向回链）。
    """
    p1, p2_in_main = split_parts(main_text)
    p2 = appendix_text if appendix_text else p2_in_main

    # Part 1：符号表单抽为折叠盒子（默认展开），以便正文编号 chip 能跳回 #symbol-table
    sym_html = ""
    m = SYM_BLOCK_RE.search(p1)
    if m:
        title, rest, got = "符号表", [], False
        for ln in m.group(1).splitlines():
            if not got and re.match(r"^#{1,6}\s+", ln):
                title = re.sub(r"^#{1,6}\s+", "", ln).strip()
                got = True
            else:
                rest.append(ln)
        sym_html = ('<details class="sym-box" id="symbol-table"><summary>%s'
                    '<span class="tag">待查 · 默认收起</span></summary>'
                    '<div class="body">%s</div></details>'
                    % (html.escape(title), render_md("\n".join(rest), base_dir)))
        p1 = p1[:m.start()] + "\n@@SYMBLOCK@@\n" + p1[m.end():]

    body1 = render_md(p1, base_dir)
    if sym_html:
        body1 = body1.replace("<p>@@SYMBLOCK@@</p>", sym_html)

    # Part 2：按 "## §X" 切成若干 <details>
    body2 = ""
    if p2.strip():
        ls = [l for l in p2.splitlines() if not l.strip().startswith("<!--")]
        # 前导内容（H1 标题 / 说明条）落在折叠区之外
        pre, k = [], 0
        while k < len(ls) and not re.match(r"^##\s+§", ls[k]):
            pre.append(ls[k])
            k += 1
        secs, cur = [], []
        for line in ls[k:]:
            if re.match(r"^##\s+§", line):
                if cur:
                    secs.append("\n".join(cur))
                cur = [line]
            else:
                cur.append(line)
        if cur:
            secs.append("\n".join(cur))
        blocks = []
        for sec in secs:
            if not sec.strip():
                continue
            head = sec.splitlines()[0]
            sid = _slug(re.sub(r"^#+\s*", "", head))
            inner = render_md("\n".join(sec.splitlines()[1:]), base_dir)
            openattr = " open" if open_all else ""
            blocks.append('<details id="sec-%s"%s><summary>%s</summary>'
                          '<div class="body">%s</div></details>'
                          % (sid, openattr, inline_md(re.sub(r"^#+\s*", "", head), base_dir), inner))
        intro = ('<div class="tag">Part 2 · 附录层（七步 SOP 全量）——'
                 '默认收起，点标题展开；也可右上角一次性展开全部</div>')
        body2 = ('<section class="appendix">%s%s%s</section>'
                 % (render_md("\n".join(pre), base_dir), intro, "".join(blocks)))

    return """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title>
<style>%s%s</style></head>
<body><div class="wrap">
<div class="bar">
  <span class="title">econ-indicator-reader · 三件套 v2.4 · Part 1 结论层（含外源印证 · 符号表末尾折叠）</span>
  %s
  <button id="btn-top">回到底部</button>
  <button id="btn-open">展开全部附录</button>
  <button id="btn-close">收起全部附录</button>
</div>
%s
%s
</div>
<script>%s</script></body></html>
""" % ("解读卡预览", CSS, DARK_OVERRIDE if dark else "",
       "".join('<a class="blink" href="%s">%s</a>' % (h, l) for h, l in links),
       body1, body2, JS)


def build_html_brief(text, base_dir, dark=False, links=()):
    """v2.4 快读卡（第三形态）→ 单页自包含 HTML：首屏直呈，符号末尾折叠，顶栏回链。

    快读卡不是主卡的子集，是三件套的「30 秒腿」：本页只呈现 VISUAL 区块 + 审计锚点 +
    免责 + 折叠的符号表；判定清单与外源台账一律回链主卡/附录，本页不复制。
    """
    vis = VISUAL_BLOCK_RE.search(text)
    visual = vis.group(1) if vis else text          # 首屏：直接呈现，不折叠
    rest = VISUAL_BLOCK_RE.sub("", text).strip()

    sym_html = ""
    sm = SYM_BLOCK_RE.search(rest)
    if sm:
        title, body_lines, got = "符号表", [], False
        for ln in sm.group(1).splitlines():
            if not got and re.match(r"^#{1,6}\s+", ln):
                title = re.sub(r"^#{1,6}\s+", "", ln).strip()
                got = True
            else:
                body_lines.append(ln)
        sym_html = ('<details class="sym-box" id="symbol-table"><summary>%s'
                    '<span class="tag">待查 · 默认收起</span></summary>'
                    '<div class="body">%s</div></details>'
                    % (html.escape(title), render_md("\n".join(body_lines), base_dir)))
        rest = rest[:sm.start()] + "\n@@SYMBLOCK@@\n" + rest[sm.end():]

    body_rest = render_md(rest, base_dir)
    if sym_html:
        body_rest = body_rest.replace("<p>@@SYMBLOCK@@</p>", sym_html)

    bar_links = "".join('<a class="blink" href="%s">%s</a>' % (href, label) for href, label in links)
    bar = ('<div class="bar"><span class="title">econ-indicator-reader · 快读卡 v2.4（第三形态 · '
           '三件套首屏）—— 判定与台账见主卡 / 附录，回链在顶栏</span>%s'
           '<button id="btn-top">回到顶部</button>'
           '<button id="btn-expand">展开符号表</button></div>' % bar_links)
    return """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title>
<style>%s%s</style></head>
<body><div class="wrap">
%s
<div class="lead">本卡＝30 秒首屏。想看判定怎么来的、信源台账在哪 → 顶栏回链「主卡 / 附录」。</div>
%s
%s
</div>
<script>%s</script></body></html>
""" % ("快读卡预览", CSS, DARK_OVERRIDE if dark else "",
       bar, body_rest, body_visual_block(visual, base_dir), JS)


def body_visual_block(visual, base_dir):
    """首屏直接呈现（不套 <details>），只在前面放一行层级说明。"""
    # 卡片自带 H1（「快读卡 · …」），这里只补一行层级标签，不再重复一个 H1
    return ('<div class="onepager"><div class="tag" style="margin-bottom:12px">'
            '三件套首屏 · 不折叠 · 30 秒读完</div>%s</div>'
            % render_md(visual, base_dir))


def main():
    ap = argparse.ArgumentParser(description="解读卡（双层 / 三层）→ 单页自包含 HTML 预览")
    ap.add_argument("card", help="主卡 md")
    ap.add_argument("appendix", nargs="?", help="附录 md（缺省自动发现 <stem>_appendix.md）")
    ap.add_argument("-o", "--out", help="输出 html 路径")
    ap.add_argument("--open-appendix", action="store_true", help="附录默认全部展开")
    ap.add_argument("--dark", action="store_true", help="深色主题")
    a = ap.parse_args()

    card = a.card
    if not os.path.isfile(card):
        print("文件不存在: %s" % card)
        return 2
    base_dir = os.path.dirname(os.path.abspath(card))
    app = a.appendix
    if not app or not os.path.isfile(app):
        # 只取文件名做拼接：card 可能是相对路径，拼接前已用 base_dir 归一
        stem_b = os.path.splitext(os.path.basename(card))[0]
        ext_b = os.path.splitext(card)[1]
        cand = os.path.join(base_dir, stem_b + "_appendix" + ext_b)
        app = cand if os.path.isfile(cand) else None

    main_text = open(card, encoding="utf-8").read()
    app_text = open(app, encoding="utf-8").read() if app else None
    out = a.out or os.path.splitext(card)[0] + ".html"

    is_brief = os.path.splitext(card)[0].endswith("_brief")
    if is_brief:
        # 三件套回链：快读卡 → 主卡（结论层）+ 附录（审计底本），同目录同名
        stem = os.path.splitext(os.path.basename(card))[0][: -len("_brief")]
        links = []
        for suf, label in ((".md", "主卡"), ("_appendix.md", "附录")):
            tgt = stem + suf
            if os.path.isfile(os.path.join(base_dir, tgt)):
                links.append((tgt, label))
        html_doc = build_html_brief(main_text, base_dir, a.dark, tuple(links))
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        open(out, "w", encoding="utf-8").write(html_doc)
        print("已生成: %s" % out)
        print("  快读卡 %s ＋ 回链 %s" % (os.path.basename(card),
                                        " / ".join(l for _, l in links) or "（无）"))
        print("  首屏直呈 ｜ 符号表末尾折叠 ｜ 主题 %s" % ("深色" if a.dark else "浅色"))
        return 0

    # 主卡顶栏回链：附录 + 快读卡（三件套双向）
    stem_b = os.path.splitext(os.path.basename(card))[0]
    bar_links = []
    for suf, label in (("_appendix.md", "附录"), ("_brief.md", "快读卡")):
        if os.path.isfile(os.path.join(base_dir, stem_b + suf)):
            bar_links.append((stem_b + suf, label))
    html_doc = build_html(main_text, app_text, base_dir, a.open_appendix, a.dark,
                          tuple(bar_links))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    open(out, "w", encoding="utf-8").write(html_doc)
    print("已生成: %s" % out)
    print("  主卡 %s ＋ 附录 %s" % (os.path.basename(card),
                                    os.path.basename(app) if app else "（无）"))
    print("  %d KB ｜ 附录默认%s ｜ 主题 %s"
          % (os.path.getsize(out) // 1024,
             "展开" if a.open_appendix else "收起",
             "深色" if a.dark else "浅色"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
