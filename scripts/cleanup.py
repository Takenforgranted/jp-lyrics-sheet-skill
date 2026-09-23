# -*- coding: utf-8 -*-
"""
收尾清理：删掉跑歌词表时产生的缓存与中间过渡文件。

设计原则（保守第一）：
  * 默认 **dry-run**，只打印将要删除的清单；加 --apply 才真删。
  * 只删**白名单模式**命中的文件，不做任何递归通配式删除。
  * 源数据 *.json、--keep 指定的成品、.workbuddy/ 一律保护。
  * 默认只扫工作目录一层；--recursive 才递归（仍受同一白名单约束）。

用法：
  python cleanup.py --work-dir .                       # 预演
  python cleanup.py --work-dir . --apply               # 真删
  python cleanup.py --work-dir . --apply --keep out.pdf,out.html
  python cleanup.py --skill --apply                    # 清 skill 内部 _smoke/ 与 __pycache__
  python cleanup.py --temp --apply                     # 清 %TEMP% 下的 jpsheet_* 残留
  python cleanup.py --work-dir . --apply --include-data  # 连源数据 JSON 一起清
"""

import argparse
import fnmatch
import os
import shutil
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------- 白名单
# 只删这些模式命中的东西。要新增就往这两个列表里加，别改成"除了成品都删"。
FILE_PATTERNS = [
    # 抓网页 / 解析歌词的中间产物
    "raw_*.txt", "wt_*.txt", "page_*.html", "lyric_*",
    "*_parsed.txt", "*_segments.txt", "*_dump.txt", "*_romaji.txt",
    # 一次性脚本（取词/解析/探测/核对）
    "fetch*.py", "parse*.py", "parse2.py", "probe_*.py", "dump_*.py",
    "check_*.py", "scrape*.py", "inspect*.py", "calc_*.py", "render*.py",
    # 日志与临时记录
    "*.log", "*_log.txt", "build*.txt", "final*.txt", "gen_log.txt",
    "cleanup.txt", "clean*.txt", "*.tmp", "*.bak",
    # 渲染预览
    "preview_p*.png", "*_page*.png",
]

DIR_PATTERNS = [
    "preview", "_smoke", "__pycache__", ".cache", "tmp", "_tmp",
    # 抓网页时落地的 HTML dump
    "dump", "dumps",
]

# 永远不碰
PROTECTED_DIRS = {".workbuddy", ".git", "scripts", "references", "assets"}
PROTECTED_FILES = {"SKILL.md"}


def _match(name, patterns):
    n = name.lower()
    return any(fnmatch.fnmatch(n, p.lower()) for p in patterns)


def collect(work_dir, recursive, keep, include_data):
    """返回 (待删文件, 待删目录, 跳过说明)。"""
    keep = {os.path.abspath(k) for k in keep}
    files, dirs, skipped = [], [], []

    entries = [os.path.join(work_dir, e) for e in os.listdir(work_dir)]
    for p in sorted(entries):
        base = os.path.basename(p)
        if os.path.isdir(p):
            if base in PROTECTED_DIRS:
                skipped.append("%s（受保护目录，跳过）" % base)
                continue
            if _match(base, DIR_PATTERNS):
                dirs.append(p)
            elif recursive:
                collect_into(p, files, dirs, keep, include_data)
            continue

        if base in PROTECTED_FILES or os.path.abspath(p) in keep:
            skipped.append("%s（受保护/成品，跳过）" % base)
            continue
        if not include_data and base.lower().endswith(".json"):
            skipped.append("%s（源数据，加 --include-data 才会清）" % base)
            continue
        if _match(base, FILE_PATTERNS):
            files.append(p)

    return files, dirs, skipped


def collect_into(d, files, dirs, keep, include_data):
    for root, dnames, fnames in os.walk(d):
        dnames[:] = [x for x in dnames if x not in PROTECTED_DIRS]
        if os.path.basename(root) in DIR_PATTERNS:
            dirs.append(root)
            dnames[:] = []
            continue
        for f in fnames:
            p = os.path.join(root, f)
            if os.path.abspath(p) in keep:
                continue
            if not include_data and f.lower().endswith(".json"):
                continue
            if _match(f, FILE_PATTERNS):
                files.append(p)


def human(n):
    if n < 1024:
        return "%d B" % n
    if n < 1024 * 1024:
        return "%.1f KB" % (n / 1024)
    return "%.1f MB" % (n / 1024 / 1024)


def size_of(p):
    if os.path.isfile(p):
        return os.path.getsize(p)
    total = 0
    for root, _, fs in os.walk(p):
        for f in fs:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def report(title, paths, apply_):
    if not paths:
        print("%s 无" % title)
        return 0
    total = 0
    print("%s (%d)" % (title, len(paths)))
    for p in paths:
        s = size_of(p)
        total += s
        verb = "已删除" if apply_ else "将删除"
        print("  [%s] %-60s %s" % (verb, p, human(s)))
    print("  小计 %s" % human(total))
    return total


def temp_hits():
    """%TEMP% 下 Chrome 无头打印残留的 jpsheet_* 目录。"""
    t = tempfile.gettempdir()
    return [os.path.join(t, d) for d in os.listdir(t)
            if d.startswith("jpsheet_") and os.path.isdir(os.path.join(t, d))]


def skill_hits():
    """skill 内部的 _smoke/ 与 __pycache__。"""
    hits = []
    p = os.path.join(SKILL, "_smoke")
    if os.path.isdir(p):
        hits.append(p)
    for root, dnames, _ in os.walk(SKILL):
        for d in list(dnames):
            if d == "__pycache__":
                hits.append(os.path.join(root, d))
    return hits


def main():
    ap = argparse.ArgumentParser(description="歌词表流水线收尾清理")
    ap.add_argument("--work-dir", default=".", help="工作目录，默认当前目录")
    ap.add_argument("--apply", action="store_true", help="真删（默认只预演）")
    ap.add_argument("--keep", default="", help="逗号分隔，必须保留的成品路径")
    ap.add_argument("--include-data", action="store_true", help="连源数据 *.json 一起清")
    ap.add_argument("--recursive", action="store_true", help="递归子目录")
    ap.add_argument("--temp", action="store_true", help="额外清 %TEMP% 下的 jpsheet_* 残留")
    ap.add_argument("--skill", action="store_true", help="额外清 skill 内部 _smoke/ 与 __pycache__")
    ap.add_argument("--pattern", default="",
                    help="逗号分隔，追加的一次性文件名模式（如 verify*.txt,dbg*.txt）")
    args = ap.parse_args()

    work = os.path.abspath(args.work_dir)
    keep = [k.strip() for k in args.keep.split(",") if k.strip()]
    for p in [x.strip() for x in args.pattern.split(",") if x.strip()]:
        if p not in FILE_PATTERNS:
            FILE_PATTERNS.append(p)
    # --include-data 时把 *.json 纳入可删白名单（否则只是解除保护、仍不会命中任何模式）
    if args.include_data and "*.json" not in FILE_PATTERNS:
        FILE_PATTERNS.append("*.json")

    print("模式: %s" % ("APPLY（真删）" if args.apply else "DRY-RUN（预演，加 --apply 生效）"))
    print("目录: %s" % work)
    if not os.path.isdir(work):
        print("[ERR] 目录不存在")
        return 2

    files, dirs, skipped = collect(work, args.recursive, keep, args.include_data)

    extra = []
    if args.temp:
        extra += temp_hits()
    if args.skill:
        extra += skill_hits()
    dirs = dirs + extra

    total = report("中间文件", files, args.apply)
    total += report("中间目录 / 缓存目录", dirs, args.apply)

    if skipped:
        print("保留 (%d)" % len(skipped))
        for s in skipped:
            print("  - %s" % s)

    if args.apply:
        removed = 0
        for p in dirs:
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
                removed += 0 if os.path.exists(p) else 1
        for p in files:
            try:
                os.remove(p)
                removed += 1
            except OSError as e:
                print("[warn] 删不掉 %s: %s" % (p, e))
        left = [p for p in dirs if os.path.exists(p)]
        if left:
            print("[warn] 以下目录未能删除（多半被占用）：")
            for p in left:
                print("       %s" % p)
        print("\n清理完成：删除 %d 项，释放 %s" % (removed, human(total)))
    else:
        print("\n预演结束，可释放 %s —— 确认无误后加 --apply" % human(total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
