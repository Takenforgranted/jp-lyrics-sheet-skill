# -*- coding: utf-8 -*-
"""
环境自检（安装后先跑这个）

  python doctor.py           # 环境 + 罗马音自检
  python doctor.py --smoke    # 额外跑一遍样例端到端（HTML + PDF）
"""

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


OK, BAD = "[ OK ]", "[FAIL]"


def sh(args):
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="跑端到端样例")
    args = ap.parse_args()

    fail = 0

    # 1. Python
    v = sys.version_info
    good = v >= (3, 8)
    print("%s Python %d.%d.%d (%s)" % (OK if good else BAD, v.major, v.minor, v.micro, sys.executable))
    fail += 0 if good else 1

    # 2. 模块
    for mod, required in [("pypdfium2", True), ("PIL", True), ("playwright", False)]:
        try:
            __import__(mod)
            print("%s module %s" % (OK, mod))
        except Exception:
            tag = BAD if required else "[warn]"
            print("%s module %s 缺失%s" % (tag, mod, "" if required else "（可选，PDF 兜底用）"))
            fail += 1 if required else 0

    # 3. 浏览器
    from build import find_browser
    kind, path = find_browser()
    if path:
        print("%s 浏览器 %s -> %s" % (OK, kind, path))
    else:
        print("%s 没找到 Chrome / Edge / Playwright chromium，PDF 导不出" % BAD)
        fail += 1

    # 4. 字体
    fonts = {"MS Mincho": r"C:\Windows\Fonts\msmincho.ttc",
             "SimSun": r"C:\Windows\Fonts\simsun.ttc",
             "Times New Roman": r"C:\Windows\Fonts\times.ttf"}
    for name, p in fonts.items():
        if os.path.exists(p):
            print("%s 字体 %s" % (OK, name))
        else:
            print("[warn] 字体 %s 不在 %s（表格会退化到替代字体）" % (name, p))

    # 5. 罗马音规则自检
    from romaji import word_romaji
    cases = [
        ("おもいどおり", "o mo i do o ri"),
        ("いっそ", "i s so"),
        ("ひきこもって", "hi ki ko mo t te"),
        ("まわってる", "ma wa t te ru"),
        ("どう", "do u"),
        ("ラブレター", "ra bu re ta-"),
        ("しょ", "syo"),
        ("じゃ", "zya"),
        ("は", "wa"),
        ("へ", "e"),
        ("を", "o"),
        ("ちきゅう", "chi kyu u"),
        ("ナンバーワン", "na n ba- wa n"),
    ]
    bad = 0
    for src, want in cases:
        got = word_romaji(src)
        flag = OK if got == want else BAD
        if got != want:
            bad += 1
        print("%s romaji %-8s -> %-22s (期望 %s)" % (flag, src, got, want))
    fail += bad

    # 6. 配色推导：字色必须跟着底色走，且对底色保持可读对比度
    from gen_sheet import Palette, contrast, derive, _rgb
    probes = ["#e21b1b", "#f8b500", "#68be8d", "#5383c3", "#eeda01", "#c8c2c6"]
    worst = min(((c, contrast(_rgb(derive(c)[2]), _rgb(derive(c)[0]))) for c in probes),
                key=lambda x: x[1])
    if worst[1] >= 7.0:
        print("%s 配色推导 字色随底色推导，最低对比度 %.1f:1（≥7:1）" % (OK, worst[1]))
    else:
        print("%s 配色推导 对比度不足 %.1f:1 -> %s" % (BAD, worst[1], worst[0]))
        fail += 1
    pal = Palette({"X": {"color": "#e21b1b", "label": "X"}})
    pal.css_class("#e21b1b")
    if "color:" in pal.css_rules():
        print("%s 配色推导 CSS 里已写死字色（color: …）" % OK)
    else:
        print("%s 配色推导 CSS 缺 color: 规则，字色不会随底色适配" % BAD)
        fail += 1

    # 7. 端到端
    if args.smoke:
        print("\n--- smoke ---")
        out = os.path.join(SKILL, "_smoke")
        os.makedirs(out, exist_ok=True)
        html = os.path.join(out, "sample.html")
        data = os.path.join(SKILL, "assets", "sample_kaminomanimani.json")
        r = sh([sys.executable, os.path.join(HERE, "gen_sheet.py"), "--data", data, "--out", html])
        print(r.stdout.decode("utf-8", "replace").strip())
        if not os.path.exists(html):
            print("%s 样例 HTML 未生成" % BAD)
            fail += 1
        else:
            # 页首标题区是硬要求：居中曲名 + 小字居中信息栏，必须出现在正文最前面
            txt = open(html, encoding="utf-8").read()
            head = txt.split('<table class="jp-line')[0]
            for cls, what in [("jp-title", "居中曲名"), ("jp-meta", "小字信息栏")]:
                if 'class="%s"' % cls in head:
                    print("%s smoke 页首 %s 已渲染" % (OK, what))
                else:
                    print("%s smoke 页首缺 %s（HTML/PDF 开头必须有）" % (BAD, what))
                    fail += 1
            r = sh([sys.executable, os.path.join(HERE, "build.py"), html])
            print(r.stdout.decode("utf-8", "replace").strip())
            if r.returncode != 0:
                fail += 1
            # 品牌图标是硬要求：build.py 盖章到每页右上角（纸面边距区）
            pdf = os.path.join(out, "sample.pdf")
            if os.path.exists(pdf):
                try:
                    import pypdfium2 as pdfium
                    import numpy as np
                    pg = pdfium.PdfDocument(pdf)[0]
                    a = np.array(pg.render(scale=2).to_pil().convert("L"))
                    h, w = a.shape
                    zone = a[: int(h * 0.05), int(w * 0.94):]
                    if int((zone < 200).sum()) > 200:
                        print("%s smoke 品牌图标 已盖章（PDF 每页右上角）" % OK)
                    else:
                        print("%s smoke PDF 右上角没扫到品牌图标" % BAD)
                        fail += 1
                except Exception as e:
                    print("[warn] 品牌图标像素断言跳过：%s" % e)
            else:
                print("%s smoke 未产出 sample.pdf" % BAD)
                fail += 1

    print("\n结论: %s" % ("PASS" if fail == 0 else "FAIL (%d 项)" % fail))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
