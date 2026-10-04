# Word 原生方程管线（pandoc → OMML）

适用：任何要落 Word 的正文公式（行内与展示式）。产出的方程**可双击编辑、矢量、与正文同源**。

## 1. 环境

受管 venv 安装：`pip install pypandoc-binary`
`pypandoc.get_pandoc_path()` 即拿到 pandoc 可执行文件。**无需 TeX Live / MiKTeX**。

> 踩坑：GitHub release 直连下载 pandoc zip 会被节流截断成 3.8MB 空壳
> （文件头是 PK 但 zipfile 报 BadZipFile）。改走 PyPI 通道最稳。

## 2. 核心调用（零临时文件）

pypandoc 高层 API `convert_text(..., outputfile=)` 必须落盘；而**每公式写临时 docx 再删除**
会触发删除类拦截导致构建被拒。正确做法：让 pandoc 把 docx 输出到 stdout。

```python
import subprocess, pypandoc, io
from docx import Document
from docx.oxml.ns import qn

exe = pypandoc.get_pandoc_path()
src = f"${latex}$"                       # 单条公式用 $...$ 包裹
p = subprocess.run([exe, "-f", "latex", "-t", "docx", "-o", "-"],
                   input=src.encode("utf-8"), capture_output=True)
d = Document(io.BytesIO(p.stdout))       # 内存解析，零临时文件、零删除
for para in d.paragraphs:
    el = para._p.find(qn("m:oMath"))
```

## 3. 五个真实踩坑（本项目实证）

1. **中文进数学模式会变方框**：`\text{人民币贬值}` 在 OMML 内缺字形。
   → 替换为 `\mathrm{...}` 承载符号，中文含义移入文内注解（GLOSS）。
   例：原 `\frac{\partial Net}{\partial X} > 0 \quad \text{人民币贬值}` →
   改 `\frac{\partial Net}{\partial X} > 0` + 正文注"（e↑ 表示本币贬值）"。

2. **OMML 分式标签是 `<m:f>` 不是 `<m:frac>`**。核验结构时搜错标签会误判"公式丢失"。
   其他：下标 `<m:sSub>`、上下标 `<m:sSup>`、上划线重音 `<m:acc>`。

3. **`python-docx` 的 `paragraph.text` 读不到 OMML**。表格里填了方程的单元格在脚本视角
   显示为空是正常的，**不代表内容丢失**。核验必须查 XML：`<m:oMath` 计数 + `<m:t>` 词元。

4. **不要用 `\begin{equation}` 环境期待编号**：pandoc 对单行 `$...$` 输入最稳。
   展示式编号建议自排版：居中 tab（可用宽度一半）+ 右对齐 tab（可用宽度）+ `(n)` 编号。

5. **回退要有声**：转换失败时不要静默降级成 LaTeX 纯文本。应打印 `[warn]` 并在文末
   列出"未原生化的公式清单"，保持可核验。

## 4. 核验标准

- 文档 body 中 `<m:oMath` 计数 ≥ 源稿公式条数
- `$$` / `\frac` / `\partial` 等 LaTeX 残迹段落数 = 0
- 内嵌图片数 = 仅图表数（公式不应再以图片存在）
- 在 Word 中双击任一方程应能进入公式编辑态 —— **这是最终判据**
