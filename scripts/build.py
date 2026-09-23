# -*- coding: utf-8 -*-
"""
HTML -> PDF 导出 + 渲染 PNG 目检（浏览器自动探测）

原 SKILL.md 写死了 Edge 路径，但很多机器上只有 Chrome（或只有 Playwright 的
chromium）。这里按优先级自动探测，探测不到就直接报清楚。

用法：
  python build.py sheet.html                  # 同目录产出 sheet.pdf + 预览 PNG
  python build.py sheet.html --out out.pdf
  python build.py sheet.html --png-dir .  --pages 3
  python build.py --browser                   # 只打印探测到的浏览器
"""

import argparse
import os
import subprocess
import sys
import tempfile
import pathlib

import shutil

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ---------------------------------------------------------------- 浏览器探测
# 注意：这里只用系统环境变量（%LOCALAPPDATA% / %PROGRAMFILES%），
# 绝不写死 C:\Users\<真实用户名>\…，保证 skill 可直接分享。
CANDIDATES = [
    ("chrome", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    ("chrome", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ("chrome", r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ("edge", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    ("edge", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ("edge", r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
]


def find_browser():
    """返回 (kind, path)。找不到返回 (None, None)。"""
    for kind, path in CANDIDATES:
        p = os.path.expandvars(path)
        if os.path.exists(p):
            return kind, p
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            exe = p.chromium.executable_path
            if exe and os.path.exists(exe):
                return "playwright-chromium", exe
    except Exception:
        pass
    return None, None


def to_file_url(path):
    return pathlib.Path(os.path.abspath(path)).as_uri()


# ---------------------------------------------------------------- 打印
def html_to_pdf(html_path, pdf_path, browser_path, timeout=180):
    """Edge/Chrome 系无头打印。返回 (ok, msg)。"""
    tmp = tempfile.mkdtemp(prefix="jpsheet_")
    # 注意：--print-to-pdf 的值不要加引号。这里用 subprocess 列表传 argv，
    # 加引号会被 Chrome 当成文件名的一部分 -> 0x7B「文件名语法不正确」。
    # （在 PowerShell 里手敲时加引号是 shell 帮你剥掉的，两回事。）
    cmd = [
        browser_path,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--no-sandbox",
        "--user-data-dir=" + tmp,
        '--print-to-pdf=%s' % os.path.abspath(pdf_path),
        to_file_url(html_path),
    ]
    try:
        r = subprocess.run(cmd, timeout=timeout,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.TimeoutExpired:
        return False, "打印超时（%ss）" % timeout
    except FileNotFoundError:
        return False, "浏览器不存在：%s" % browser_path
    finally:
        # Chrome 临时 profile：每次打印都会在 %TEMP% 留下一个 jpsheet_* 目录，必须回收
        shutil.rmtree(tmp, ignore_errors=True)

    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
        return True, "PDF 已生成"
    err = (r.stderr or b"").decode("utf-8", "replace")[:500]
    return False, "未产出 PDF。stderr: %s" % err


def html_to_pdf_playwright(html_path, pdf_path, timeout=120000):
    """兜底：用 Playwright 的 chromium 打印（print_background 保证粉色底不丢）。"""
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        return False, "Playwright 不可用：%s" % e
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            pg = br.new_page()
            pg.goto(to_file_url(html_path), wait_until="load", timeout=timeout)
            pg.emulate_media(media="print")
            pg.pdf(path=os.path.abspath(pdf_path), format="A4", print_background=True,
                   margin={"top": "14mm", "bottom": "14mm", "left": "10mm", "right": "10mm"})
            br.close()
        return True, "PDF 已生成（Playwright）"
    except Exception as e:
        return False, "Playwright 打印失败：%s" % e


def pdf_to_png(pdf_path, png_dir, pages=3):
    """pypdfium2 渲染前 N 页 PNG，用于目检。"""
    try:
        import pypdfium2 as pdfium
    except Exception as e:
        return [], "pypdfium2 不可用：%s" % e
    os.makedirs(png_dir, exist_ok=True)
    doc = pdfium.PdfDocument(pdf_path)
    total = len(doc)
    outs = []
    for i in range(min(pages, total)):
        png = os.path.join(png_dir, "preview_p%d.png" % (i + 1))
        doc[i].render(scale=2).to_pil().save(png)
        outs.append(png)
    return outs, "共 %d 页" % total


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description="日语歌词表 HTML -> PDF")
    ap.add_argument("html", nargs="?", help="输入 HTML")
    ap.add_argument("--out", help="输出 PDF（默认与 HTML 同名 .pdf）")
    ap.add_argument("--png-dir", help="预览 PNG 输出目录（默认 PDF 同目录）")
    ap.add_argument("--pages", type=int, default=3, help="预览页数，默认 3")
    ap.add_argument("--no-png", action="store_true", help="跳过 PNG 预览")
    ap.add_argument("--browser", action="store_true", help="只打印探测到的浏览器")
    args = ap.parse_args()

    kind, path = find_browser()

    if args.browser:
        print("浏览器: %s\n路径:   %s" % (kind, path))
        return 0 if path else 1

    if not args.html:
        print("[ERR] 需要输入 HTML")
        return 2
    if not kind:
        print("[ERR] 没找到 Chrome / Edge / Playwright chromium，无法导出 PDF。")
        print("      可安装 Chrome，或 pip install playwright && playwright install chromium")
        return 1
    print("[INFO] 浏览器: %s (%s)" % (kind, path))

    html = os.path.abspath(args.html)
    pdf = os.path.abspath(args.out or os.path.splitext(html)[0] + ".pdf")

    if kind == "playwright-chromium":
        ok, msg = html_to_pdf_playwright(html, pdf)
    else:
        ok, msg = html_to_pdf(html, pdf, path)
    if not ok:
        print("[ERR] " + msg)
        if kind != "playwright-chromium":
            print("[INFO] 尝试 Playwright 兜底…")
            ok, msg = html_to_pdf_playwright(html, pdf)
        if not ok:
            print("[ERR] " + msg)
            return 1
    print("[OK] %s (%d 字节) — %s" % (pdf, os.path.getsize(pdf), msg))

    if not args.no_png:
        png_dir = args.png_dir or os.path.dirname(pdf) or "."
        outs, msg = pdf_to_png(pdf, png_dir, args.pages)
        print("[INFO] %s" % msg)
        for p in outs:
            print("[PNG] " + p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
