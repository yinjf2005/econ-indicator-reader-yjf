# _shared/vizmath — 论文/研报的「图形 + 公式」共享枢纽

> 本目录不是可 @ 调用的独立技能，而是**被其他技能引用的公共资产**。
> 目的：任何报告/论文类技能在产出图表与公式时，**无需反复安装或 @ 调用**
> scientific-visualization / pandoc，直接按本目录绝对路径取用即可。

## 一、职责边界（去重裁断，2026-09-26 用户确认）

| 产出物 | 唯一走法 | 由谁提供 | 为什么不能用另一个 |
|---|---|---|---|
| 正文行内 / 展示公式（要可编辑、可选中） | pandoc → Word 原生 **OMML** | `scripts/tex2omml.py` | 图片公式在 Word 内不可编辑、字体与正文不同源 |
| 数据图表（折线/柱/散点/多面板/流程示意） | scientific-visualization 样式 + 导出 | `scripts/render_figure.py` | pandoc 不能画图 |
| 图表内部的数学标注（轴标签希腊字母、图内注公式） | matplotlib mathtext（必选） | 内建于绘图过程 | OMML 无法嵌进图片，此处必须用 mathtext |
| 整篇 md → docx 排版（三线表、标题层级、中文字体） | python-docx 自建管线 | 各技能既有脚本 | pandoc 版面控制弱，给不了中文三线表与 Heading 层级 |

**唯一交叉点**：两者都能渲染数学符号。但用途不重叠（OMML 服务正文可编辑方程，
mathtext 服务图片内部标注），故**不合并**，按上表分工。

## 二、与既有内置规范的优先级

- `academic-paper` 内置的 `references/statistical_visualization_standards.md`（750 行）

  → 裁定为**回退参考**：有 scientific-visualization 可执行脚本时，主路径走脚本；
  仅当 SV 不可用时才读该文件。避免两套标准打架。
  （该文件属第三方技能，不改动其文件，此优先级由用户级路由记忆承载。）

- `report-review-nesting` 的 `scripts/md2docx.py`（180 行，python-docx 自建 md→docx）

  → 与 pandoc **互补而非重复**，不合并：pandoc 独占公式原生化，
  md2docx 独占中文三线表/标题层级。分工：**公式走 pandoc，整篇排版走 python-docx 管线**。

## 三、调用方式（技能内直接引用，不需要 @）

```python
import sys
HUB = r"C:/Users/yinjf/.workbuddy/skills/_shared/vizmath"   # Windows
# HUB = os.path.expanduser("~/.workbuddy/skills/_shared/vizmath")
sys.path.insert(0, HUB + "/scripts")

from tex2omml import omml_for, add_math_run      # 公式
from render_figure import figure_context         # 图表
```

详细管线与踩坑：
- 公式 → `refs/pandoc-omml.md`
- 图表 → `refs/journal-figures.md`

## 四、Python 环境

受管 venv：`~/.workbuddy/binaries/python/envs/default/Scripts/python.exe`
已装：matplotlib、numpy、python-docx、Pillow、pypandoc-binary（自带 pandoc 3.9，无需 TeX Live）。
