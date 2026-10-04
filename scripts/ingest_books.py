#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ingest_books.py —— 从 ima 知识库拉取书摘，落入 references/books/ 的投喂通道。

用法:
  python scripts/ingest_books.py --keyword "房地产"            # 按标题关键字搜索并下载到 _inbox/
  python scripts/ingest_books.py --keyword "房地产" --layer mechanism_liqilin
                                                              # 直接落到指定层目录
  python scripts/ingest_books.py --media-id <media_id> --layer read_ouleying
  python scripts/ingest_books.py --list                        # 列出知识库全部条目（含是否已镜像）

依赖: ima_api.cjs。自足优先——先取技能内联副本 `scripts/_vendor/ima_api.cjs`，
找不到再回退 `~/.workbuddy/skills/ima-skill/`（也可用 --ima-dir 指定）。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOKS_DIR = os.path.join(SKILL_DIR, "references", "books")
INDEX_MD = os.path.join(BOOKS_DIR, "_MIRROR_INDEX.md")
INBOX = os.path.join(BOOKS_DIR, "_inbox")

_VENDOR_IMA = os.path.join(SKILL_DIR, "scripts", "_vendor")
DEFAULT_IMA = (
    _VENDOR_IMA
    if os.path.isfile(os.path.join(_VENDOR_IMA, "ima_api.cjs"))
    else os.path.join(os.path.expanduser("~"), ".workbuddy", "skills", "ima-skill")
)
KB_ID = "ehrOmGP5tNL1aooI-8Dm6GaSpQqpkk3SdsEWC2n9lyQ="
FOLDERS = {
    "read_ouleying": "folder_7511737246950144",
    "mechanism_liqilin": "folder_7511737238582412",
    "method_nakamura": "folder_7511737234369761",
    "expectation_baumohl": "folder_7511728099175668",
}
LAYERS = list(FOLDERS.keys())


def call_ima(api, payload, ima_dir):
    r = subprocess.run(
        ["node", "ima_api.cjs", api, json.dumps(payload, ensure_ascii=False)],
        capture_output=True, text=True, cwd=ima_dir, encoding="utf-8",
    )
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError("ima_api 调用失败: " + (r.stderr or "")[:300])
    d = json.loads(r.stdout)
    if d.get("code") not in (0, "0", None):
        raise RuntimeError("ima_api 返回错误 code=%s msg=%s" % (d.get("code"), d.get("msg")))
    return d


def list_all(ima_dir):
    out = {}
    for layer, fid in FOLDERS.items():
        d = call_ima("openapi/wiki/v1/get_knowledge_list",
                     {"knowledge_base_id": KB_ID, "folder_id": fid,
                      "cursor": "", "limit": 50}, ima_dir)  # limit 上限 50
        out[layer] = [(x["title"], x["media_id"])
                      for x in d.get("data", {}).get("knowledge_list", [])]
    return out


def get_url(media_id, ima_dir):
    d = call_ima("openapi/wiki/v1/get_media_info", {"media_id": media_id}, ima_dir)
    return d["data"]["url_info"]["url"]


def safe_name(title):
    fn = re.sub(r'[\\/:*?"<>|]', "_", title).strip()
    return fn if fn.endswith(".md") else fn + ".md"


def is_mirrored(media_id):
    if not os.path.exists(INDEX_MD):
        return False
    return media_id in open(INDEX_MD, encoding="utf-8").read()


def main():
    ap = argparse.ArgumentParser(description="从 ima 拉取书摘到 books/")
    ap.add_argument("--keyword", help="标题关键字")
    ap.add_argument("--media-id", help="精确 media_id")
    ap.add_argument("--layer", choices=LAYERS, help="目标层目录；缺省落 _inbox/")
    ap.add_argument("--list", action="store_true", help="列出全部条目")
    ap.add_argument("--ima-dir", default=DEFAULT_IMA, help="ima-skill 目录")
    args = ap.parse_args()

    if not os.path.isdir(args.ima_dir):
        print("找不到 ima-skill 目录: %s（用 --ima-dir 指定）" % args.ima_dir)
        return 2

    if args.list:
        for layer, items in list_all(args.ima_dir).items():
            print("== %s (%d) ==" % (layer, len(items)))
            for t, m in items:
                print("  [%s] %s" % ("✔" if is_mirrored(m) else "○", t))
        return 0

    if not args.keyword and not args.media_id:
        print("需要 --keyword 或 --media-id（或 --list）")
        return 2

    targets = []
    if args.media_id:
        targets.append((args.media_id, args.media_id))
    else:
        for layer, items in list_all(args.ima_dir).items():
            for t, m in items:
                if args.keyword in t:
                    targets.append((t, m))
    if not targets:
        print("无匹配条目：%s" % args.keyword)
        return 1

    dest_dir = os.path.join(BOOKS_DIR, args.layer) if args.layer else INBOX
    os.makedirs(dest_dir, exist_ok=True)
    got = []
    for title, mid in targets:
        try:
            url = get_url(mid, args.ima_dir)
            path = os.path.join(dest_dir, safe_name(title))
            urllib.request.urlretrieve(url, path)
            got.append((title, path))
            print("✔ %s -> %s" % (title, path))
        except Exception as e:
            print("✘ %s : %r" % (title, e))

    print("\n已下载 %d 件到 %s" % (len(got), dest_dir))
    print("后续：判层 → 移入对应层目录 → 更新 _MIRROR_INDEX.md（○ 改 ✔）→ 跑 check.py --selftest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
