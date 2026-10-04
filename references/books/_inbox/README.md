# _inbox · 投喂预留区

新增书摘 / 方法件先落这里，判层后再移入上一层目录。

## 三步

1. **落入**：直接粘贴 md 到本目录，或拉取
   ```bash
   python scripts/ingest_books.py --keyword "房地产"     # 落到这里
   python scripts/ingest_books.py --media-id <id> --layer mechanism_liqilin   # 直接落指定层
   python scripts/ingest_books.py --list                 # 列出知识库全部条目（含是否已镜像）
   ```
   （`ingest_books.py` 优先用技能内联的 `scripts/_vendor/ima_api.cjs`，无需另装 ima-skill。）

2. **判层**：属于哪一层就移进哪个目录，文件名沿用 `<编号>_<主题>.md`

   | 目录 | 层 | 书 |
   |---|---|---|
   | `../read_ouleying/` | 读（怎么读 / 发布日历 / 可信度） | 欧乐鹰 |
   | `../mechanism_liqilin/` | 机制（怎么算 / 口径 / 联动） | 李奇霖 |
   | `../expectation_baumohl/` | 预期（预期差 / 读数纪律） | 鲍莫尔 |
   | `../method_nakamura/` | 方法（定量定性工具箱） | 中村力 |
   | `../_index/` | 各书与专题总索引 | — |

3. **登记**：更新 `../_MIRROR_INDEX.md`（该件状态 `○` → `✔` 并填本地路径；新书则新增章节）；
   若新件引入新方法，同步增补 `../../05-expectation-layer.md` 或 `../../07-pitfalls.md`；
   最后跑 `python scripts/check.py --selftest` 确认全绿。

## 注意

本目录非空是**故意的**——空目录不会进分发 zip，保留本文件可保证安装后投喂区仍然存在。请勿删除。
