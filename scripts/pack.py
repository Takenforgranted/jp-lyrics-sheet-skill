# -*- coding: utf-8 -*-
"""
把本 skill 打成可分发的 zip（平铺结构，自动排除缓存），并可一键验证。

用法：
  python pack.py --out <OUT_DIR>\\jp-lyrics-sheet.zip
  python pack.py --out <OUT_DIR>\\jp-lyrics-sheet.zip --verify

--verify 会把 zip 解到临时目录，在**解压副本**里跑：
  doctor.py --smoke + tests/test_romaji.py + desensitize.py
三者全绿才算这个包能用（跑完自动删临时目录）。

打包前请先确认 desensitize.py 输出 CLEAN，否则会把隐私带出去。
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
EXCLUDE_DIRS = {"_smoke", "__pycache__", ".git", ".workbuddy", ".venv"}


def build_zip(out_path):
    if os.path.exists(out_path):
        os.remove(out_path)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    n = 0
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for root, dirs, files in os.walk(SKILL):
            dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS)
            for f in sorted(files):
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, SKILL).replace("\\", "/"))
                n += 1
    print("[OK] %d 个文件 -> %s (%d 字节)" % (n, out_path, os.path.getsize(out_path)))
    return n


def check_zip(out_path):
    with zipfile.ZipFile(out_path) as z:
        bad = z.testzip()
        print("[%s] testzip: %s" % ("OK" if bad is None else "FAIL", bad or "完整"))
        for i in z.infolist():
            print("   %8d  %s" % (i.file_size, i.filename))
        return bad is None


def verify(out_path):
    tmp = tempfile.mkdtemp(prefix="jpsheet_pack_")
    try:
        with zipfile.ZipFile(out_path) as z:
            z.extractall(tmp)
        steps = [
            [sys.executable, os.path.join(tmp, "scripts", "doctor.py"), "--smoke"],
            [sys.executable, os.path.join(tmp, "tests", "test_romaji.py")],
            [sys.executable, os.path.join(tmp, "scripts", "desensitize.py")],
        ]
        bad = 0
        for cmd in steps:
            print("\n--- %s ---" % os.path.basename(cmd[1]))
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            print(r.stdout.decode("utf-8", "replace").strip())
            if r.returncode != 0:
                bad += 1
        print("\n验证结论: %s" % ("PASS（解压副本可用）" if not bad else "FAIL（%d 步未过）" % bad))
        return bad == 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="打包本 skill 为 zip")
    ap.add_argument("--out", required=True, help="zip 输出路径（会自动覆盖同名文件）")
    ap.add_argument("--verify", action="store_true", help="解压到临时目录跑三项自检")
    args = ap.parse_args()

    build_zip(args.out)
    ok = check_zip(args.out)
    if args.verify:
        ok = verify(args.out) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
