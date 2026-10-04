#!/usr/bin/env python
"""
Nature/Science/Cell 级期刊图表门面（包装 scientific-visualization）。

用法（本技能内联版，优先用技能内副本）：
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    from vizmath.render_figure import figure_context, export_figure

    with figure_context("nature", palette_name="okabe_ito_on_white") as ctx:
        fig, ax = plt.subplots(figsize=(6.4, 3.6), layout="constrained")
        ax.plot(x, y)
        ctx.export(fig, "chart_m1")     # 必须在 with 块内导出！

命令行自检：
    python render_figure.py --selftest      # 画一张样图，校验字体告警为 0
    python render_figure.py --list-styles
"""
import os
import sys
import warnings

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 自足优先：先找技能内联的 SV 副本，找不到再回退全局安装目录
_SV_VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor", "scientific-visualization")
SV_SKILL = _SV_VENDOR if os.path.isdir(_SV_VENDOR) else os.path.expanduser("~/.workbuddy/skills/scientific-visualization")

# CJK 字体必须列首位：font.family="sans-serif" 别名下 per-glyph 回退不可靠
CJK_FONTS = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans SC"]
LATIN_FONTS = ["Arial", "DejaVu Sans"]

# 抬到 9-10pt 以适配屏幕/Word 阅读（Nature 印刷默认 7pt）
_SIZE_OVERRIDE = {
    "font.size": 9, "axes.labelsize": 9, "axes.titlesize": 10,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
}


def _load_sv():
    for p in (os.path.join(SV_SKILL, "scripts"), os.path.join(SV_SKILL, "assets")):
        if p not in sys.path and os.path.isdir(p):
            sys.path.insert(0, p)
    try:
        import style_presets
        import figure_export
        return style_presets, figure_export
    except ImportError as e:
        raise RuntimeError(
            "未找到 scientific-visualization 技能或依赖缺失：%s\n"
            "安装目录应为：%s" % (e, SV_SKILL)
        )


class figure_context(object):
    """
    SV 样式上下文 + CJK 字体 + 可读字号，并保证导出仍在上下文内。

    关键纪律：matplotlib 在 savefig 时才解析字体，
    所以 ctx.export(...) 必须在 with 块内部调用，否则中文全部变方框。
    """

    def __init__(self, style="nature", palette_name="okabe_ito_on_white",
                 font_size=9, out_dir=None, formats=("pdf", "png"), dpi=300,
                 provenance=None, overwrite=True):
        self.style = style
        self.palette_name = palette_name
        self.font_size = font_size
        self.out_dir = out_dir or os.path.join(os.getcwd(), "assets_nature")
        self.formats = list(formats)
        self.dpi = dpi
        self.provenance = provenance or {}
        self.overwrite = overwrite
        self._ctx = None
        self._figure_export = None
        self.warnings = []

    def __enter__(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        style_presets, figure_export = _load_sv()
        self._figure_export = figure_export
        self._plt = plt
        self._ctx = style_presets.style_context(self.style, palette_name=self.palette_name)
        self._ctx.__enter__()

        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = CJK_FONTS + LATIN_FONTS
        plt.rcParams["axes.unicode_minus"] = False
        plt.rcParams.update(_SIZE_OVERRIDE)
        if self.font_size:
            delta = self.font_size - 9
            for k in ("font.size", "axes.labelsize", "axes.titlesize"):
                plt.rcParams[k] = _SIZE_OVERRIDE[k] + delta
        os.makedirs(self.out_dir, exist_ok=True)
        return self

    def export(self, fig, name, provenance=None):
        """必须在 with 块内调用：同时出 PNG(300dpi) + PDF 矢量 + export.json 溯源。"""
        dest = os.path.join(self.out_dir, name)
        prov = dict(self.provenance)
        if provenance:
            prov.update(provenance)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            report = self._figure_export.export_figure(
                fig, dest, formats=self.formats, dpi=self.dpi,
                bbox_inches=None, provenance=prov, write_manifest=True,
                overwrite=self.overwrite,
            )
        font_warns = [str(x.message) for x in caught if "missing from font" in str(x.message)]
        self.warnings.extend(font_warns)
        if font_warns:
            print("  [warn] 字体缺 %d 处（可能出现方框）: %s" % (len(font_warns), font_warns[:2]))
        self._plt.close(fig)
        print("  saved %s | %s | 字体告警=%d" % (dest, "+".join(self.formats), len(font_warns)))
        return report

    def __exit__(self, *exc):
        if self._ctx is not None:
            self._ctx.__exit__(*exc)
        self._ctx = None
        return False


def _selftest():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    import tempfile
    out = os.path.join(tempfile.gettempdir(), "vizmath_selftest_out")
    prov = {"figure_type": "selftest", "note": "示意共用来自检", "scripts": "render_figure.py"}
    with figure_context("nature", out_dir=out, provenance=prov) as ctx:
        fig, ax = plt.subplots(figsize=(6.4, 3.6), layout="constrained")
        x = np.linspace(0, 1, 100)
        ax.plot(x, x ** 2, label=r"二次项 $\alpha x^2$")
        ax.set_xlabel(r"价格敏感买家占比 $\phi$")
        ax.set_ylabel(r"收益率上行 $\Delta r$ (bp)")
        ax.legend(frameon=False)
        ctx.export(fig, "selftest_fig")
    total = len(ctx.warnings)
    files = sorted(os.listdir(out))
    print("\n产物:", files)
    print("字体告警总数:", total, "（必须为 0）")
    return 0 if total == 0 and any(f.endswith(".png") for f in files) else 1


if __name__ == "__main__":
    if "--list-styles" in sys.argv:
        style_presets, _ = _load_sv()
        try:
            import subprocess
            print(subprocess.run(
                [sys.executable, os.path.join(SV_SKILL, "scripts", "style_presets.py"), "--list"],
                capture_output=True, text=True).stdout)
        except Exception as e:
            print("列出样式失败:", e)
    else:
        sys.exit(_selftest())
