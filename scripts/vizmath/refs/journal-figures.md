# Nature/Science/Cell 级期刊图表管线（scientific-visualization）

技能本体：`~/.workbuddy/skills/scientific-visualization/`
核心资产：`assets/{nature,publication,presentation}.mplstyle`、`scripts/style_presets.py`、
`scripts/figure_export.py`、`scripts/palette_audit.py`

## 1. 标准写法（上下文必须在绘图+保存期间全程打开）

```python
from style_presets import style_context   # 需把技能 scripts/ assets/ 加入 sys.path

with style_context("nature", palette_name="okabe_ito_on_white"):
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "Arial", "DejaVu Sans"]  # CJK 必须列首位
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(6.4, 3.6), layout="constrained")
    ...
    export_figure(fig, dest, formats=["pdf", "png"], dpi=300,
                  provenance={...}, write_manifest=True)   # 必须在这个 with 块内
    plt.close(fig)
```

## 2. 三个真实踩坑（本项目实证，务必遵守）

1. **`export/savefig` 必须写在 `with` 块内部**。
   matplotlib 在 `savefig` 时才解析字体，若上下文已退出，rcParams 回退默认 DejaVu，
   **中文全部变 tofu（方框）**。曾把 `save()` 写在块外导致整批图报废。

2. **CJK 字体必须在列表首位**。写成 `["Arial", "Microsoft YaHei", ...]` 时，
   `font.family="sans-serif"` 别名下 per-glyph 回退不可靠，Arial 缺字直接落 DejaVu 照样出方框。
   正确：`["Microsoft YaHei", "Arial", "DejaVu Sans"]`。
   验证标准：运行的字体告警数须为 **0**（捕获 `UserWarning ... missing from font`）。

3. **Nature 规范：图内不放标题**，标题由 Word 题注承担；多面板图仅留 `(a)` `(b)` 面板标号。
   "（示意）"之类标注移入题注，不进图内。

## 3. 可访问性冗余编码（必做）

颜色之外再加一层：线型 / 标记（▲●■）/ 填充斜线。调色板默认 `okabe_ito_on_white`（色盲安全）。
负向区域用斜线填充而非仅靠颜色区分。

## 4. 导出与溯源

`export_figure` 一次出 PNG（300dpi，嵌 docx）+ **PDF 矢量**（投稿备用），并落 `export.json` 溯源清单。
provenance 应写明：是否示意图、数据来源、生成脚本。
**注意**：`export_figure` 默认拒绝静默覆盖（`overwrite=False`），重跑前须清产物目录或传 `overwrite=True`。

## 5. 别踩的红线

- 不得声称"自动符合 Nature 投稿要求"——只能说"按 Nature 视觉规范排版"。
- 示意图必须在图注与 provenance 双重标注，坐标取值不得冒充估计结果。
- 禁止 JPEG 出图。
