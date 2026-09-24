# -*- coding: utf-8 -*-
"""
HTML -> PDF 导出 + 渲染 PNG 目检（浏览器自动探测）

原 SKILL.md 写死了 Edge 路径，但很多机器上只有 Chrome（或只有 Playwright 的
chromium）。这里按优先级自动探测，探测不到就直接报清楚。

品牌图标盖章：PDF 产出后，用 PyMuPDF 把 skill 图标（assets/icon.png）盖到
**每一页**的右上角——位置在纸面顶边距+右边距交角处（A4 上边距 14mm、右边距
10mm，图标 8.5mm 见方完全落在边距里），物理上不与任何正文重叠，也不影响
HTML 排版与分页。图标缺失或 PyMuPDF 未安装时跳过并警告，不让导出失败。

用法：
  python build.py sheet.html                  # 同目录产出 sheet.pdf + 预览 PNG
  python build.py sheet.html --out out.pdf
  python build.py sheet.html --png-dir .  --pages 3
  python build.py sheet.html --no-brand       # 不盖品牌图标
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

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_PATH = os.path.join(SKILL, "assets", "icon.png")


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


# ---------------------------------------------------------------- 品牌图标盖章
# A4 纸面 595.28 x 841.89 pt。上边距 14mm(39.7pt)、右边距 10mm(28.35pt)，
# 图标 24pt(8.5mm) 见方，全部落在边距交角里 —— 与正文版面零重叠。
ICON_SIZE_PT = 24.0
ICON_TOP_PT = 9.0      # 距纸顶 9pt ≈ 3.2mm
ICON_RIGHT_PT = 5.0    # 距纸右缘 5pt ≈ 1.8mm


def stamp_brand(pdf_path, icon_path=ICON_PATH):
    """把品牌图标盖到 PDF 每一页右上角。返回 (ok, msg)。

    用 PyMuPDF(fitz) 做页面级插入，不改文字层、不动内容流其余部分；
    成功后原子替换原文件。
    """
    if not os.path.exists(icon_path):
        return False, "缺图标文件 %s，跳过盖章" % icon_path
    try:
        try:
            import pymupdf as fitz  # PyMuPDF 新名（>=1.24）
        except ImportError:
            import fitz  # 旧名兜底
    except Exception as e:
        return False, "PyMuPDF 不可用（pip install pymupdf），跳过盖章：%s" % e
    try:
        doc = fitz.open(pdf_path)
        tmp = pdf_path + ".brand.tmp"
        for page in doc:
            w = page.rect.width
            x1 = w - ICON_RIGHT_PT
            x0 = x1 - ICON_SIZE_PT
            y0 = ICON_TOP_PT
            y1 = y0 + ICON_SIZE_PT
            page.insert_image(fitz.Rect(x0, y0, x1, y1), filename=icon_path)
        doc.save(tmp, garbage=3, deflate=True)
        doc.close()
        os.replace(tmp, pdf_path)
        return True, "品牌图标已盖到每页右上角"
    except Exception as e:
        return False, "盖章失败（PDF 本体不受影响）：%s" % e


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
    ap.add_argument("--no-brand", action="store_true", help="不盖品牌图标（仅续页/片段用）")
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

    if not args.no_brand:
        ok2, msg2 = stamp_brand(pdf)
        print("[OK] %s" % msg2 if ok2 else "[warn] %s" % msg2)

    if not args.no_png:
        png_dir = args.png_dir or os.path.dirname(pdf) or "."
        outs, msg = pdf_to_png(pdf, png_dir, args.pages)
        print("[INFO] %s" % msg)
        for p in outs:
            print("[PNG] " + p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
