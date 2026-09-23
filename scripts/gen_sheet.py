# -*- coding: utf-8 -*-
"""
日语歌词逐词分解表生成器（数据驱动，支持角色配色）

把 JSON 歌词数据渲染成《神のまにまに》同款六行表格 HTML。
样式（含配色规则）完全写在下面的 CSS / 配色常量里，改样式只改这一处。

用法：
  python gen_sheet.py --data song.json --out out.html
  python gen_sheet.py --data song.json --out out.html --legend
  python gen_sheet.py --data song.json --check          # 只做数据体检，不产出
  python gen_sheet.py --data song.json --palettes       # 打印本曲用到的配色

数据结构（v1）：
{
  "title": "Mix shake!!",           # 页首居中显示的曲名（不要塞歌手等附加信息）
  "meta": {                          # 曲名下方的小字信息栏，按书写顺序居中排列
    "歌":     "スリーズブーケ（日野下花帆・乙宗梢）",
    "作詞":   "ケリー",
    "作曲・編曲": "川崎智哉",
    "Center": "乙宗梢"
  },
  "scheme": "spec",
  "palette": {                       # 角色/团队配色表（可选）
    "花帆": {"color": "#f8b500", "label": "日野下花帆"},
    "梢":   {"color": "#68be8d", "label": "乙宗梢"},
    "合唱": {"color": "#da645f", "label": "スリーズブーケ（合唱）"}
  },
  "blocks": [
    {"id": "サビ", "singer": "合唱", "lines": [
        {"singer": "花帆",           # 行级覆盖块级；不写则继承块级 / 默认粉
         "words": [
            {"kana": "おもいどおり", "kanji": "思い通り", "grammar": "名詞", "gloss": "如愿"}
         ],
         "trans": "尽是不如意的事"}
    ]},
    {"ref": "サビ"}                  # 重复段落：引用已有 id，数据只写一次
  ]
}

字段说明：
  kana     必填  假名行（全平假名；外来语/英文唱词写片假名读法）
  kanji    选填  写法行（歌词原文，含汉字；默认等于 kana）
  grammar  选填  语法标注（中文术语，见 references/grammar_terms.md）
  gloss    选填  词义（2-6 字短注释）
  romaji   选填  手写罗马音；不填则由 kana 自动生成
  trans    选填  整句翻译（合并单元格）

页首标题区（成品硬要求，不要关）：
  正文第一屏顶部必须是 **居中曲名**（title），其下紧跟一行 **小字居中的信息栏**
  （meta，罗列 作詞 / 作曲 / 編曲 / 歌 等）。HTML 与 PDF 都要有，位置在表格之前。
  实现集中在 render_header() + CSS 里的 div.jp-title / div.jp-meta，改样式只改这两处。
  title 只放曲名，歌手/作词等信息一律进 meta；meta 是 dict，键序即书写顺序，
  渲出成「键：值」，项与项之间自动留白、超宽自动换行，整块居中。
  只有做「续页/局部片段」时才允许加 --no-title 关掉。

配色规则：
  由角色代表色 HSL 推导 —— 填充色 = 同色相、同饱和、亮度 90%；
  边框色 = 同色相、亮度 32%（饱和上限 0.62）。未指定 singer 时沿用
  参考版固定粉（填充 #f3d7d7 / 边框 #6e3636）。
  已知配色登记在 references/colors.md。
"""

import argparse
import colorsys
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from romaji import word_romaji  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_FILL = "#f3d7d7"
DEFAULT_BORDER = "#6e3636"


# ---------------------------------------------------------------- 配色
def _rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(c * 255))) for c in rgb)


def derive(color):
    """代表色 -> (填充色, 边框色)。亮度 90% / 32%，色相饱和沿用。"""
    r, g, b = _rgb(color)
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    fill = colorsys.hls_to_rgb(hh, 0.90, ss)
    border = colorsys.hls_to_rgb(hh, 0.32, min(ss, 0.85))
    return _hex(fill), _hex(border)


class Palette:
    """把颜色字符串映射成 CSS class，避免重复规则。"""

    def __init__(self, palette=None, registry=None):
        # 注册表先载入，数据里的 palette 可覆盖同名条目
        merged = dict(registry or {})
        merged.update(palette or {})
        self.names = merged
        self.map = {}       # hex -> class name
        self.order = []

    def resolve(self, singer, fallback=None):
        """singer 可以是调色板名，也可以是 #hex；返回 hex 或 None。"""
        if not singer:
            return fallback
        if singer.startswith("#"):
            return singer
        entry = self.names.get(singer)
        if isinstance(entry, dict):
            return entry.get("color")
        if isinstance(entry, str):
            return entry
        return fallback

    def css_class(self, color):
        if not color:
            return ""
        color = color.lower()
        if color not in self.map:
            idx = len(self.map)
            self.map[color] = "cc%d" % idx
            self.order.append(color)
        return self.map[color]

    def css_rules(self):
        out = []
        for color in self.order:
            cls = self.map[color]
            fill, border = derive(color)
            out.append("table.jp-line.%s td { background: %s; border-color: %s; }"
                       % (cls, fill, border))
        return "\n".join(out)

    def legend_html(self):
        if not self.names or not self.map:
            return ""
        # 按颜色去重：注册表先入位，数据里的同名色后写覆盖其标签
        by_color = {}
        for name, entry in self.names.items():
            if isinstance(entry, dict):
                color, label = entry.get("color"), entry.get("label", name)
            else:
                color, label = entry, name
            if color:
                by_color.setdefault(color.lower(), label)
        items = []
        for cl, label in by_color.items():
            if cl not in self.map:
                continue          # 只显示本曲实际用到的角色
            fill, border = derive(cl)
            items.append(
                '<span class="jp-lg"><i style="background:%s;border-color:%s"></i>%s</span>'
                % (fill, border, label))
        return '<div class="jp-legend">%s</div>' % "".join(items) if items else ""


# ---------------------------------------------------------------- 样式
CSS = """
@page { size: A4; margin: 14mm 10mm; }
html, body { background: #ffffff; margin: 0; padding: 0; }
body { font-family: "SimSun", "宋体", serif; }

/* 页首：居中曲名 + 小字信息栏 */
div.jp-title {
  text-align: center;
  font-family: "MS Mincho", "ＭＳ 明朝", "MS PMincho", serif;
  font-size: 19px;
  color: #232323;
  letter-spacing: .06em;
  margin: 0 auto 5px auto;
  page-break-after: avoid;
}
div.jp-meta {
  text-align: center;
  font-family: "SimSun", "宋体", serif;
  font-size: 10.5px;
  color: #666666;
  line-height: 1.7;
  margin: 0 auto 12px auto;
  page-break-after: avoid;
}
div.jp-meta span.jp-mi { margin: 0 8px; white-space: nowrap; }

table.jp-line {
  border-collapse: collapse;
  margin: 11px auto;
  page-break-inside: avoid;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
table.jp-line td {
  background: {fill};
  border: 1px solid {border};
  padding: 3px 7px;
  text-align: center;
  vertical-align: middle;
  white-space: nowrap;
}
td.r-romaji { font-family: "Times New Roman", Times, serif; font-size: 10.5px;
              text-transform: lowercase; }
td.r-kana   { font-family: "MS Mincho", "ＭＳ 明朝", "MS PMincho", serif; font-size: 11.5px; }
td.r-kanji  { font-family: "MS Mincho", "ＭＳ 明朝", "MS PMincho", serif; font-size: 13.5px; }
td.r-gram   { font-family: "SimSun", "宋体", serif; font-size: 10.5px; }
td.r-gloss  { font-family: "SimSun", "宋体", serif; font-size: 12px; }
td.r-trans  { font-family: "SimSun", "宋体", serif; font-size: 12px; letter-spacing: .08em; }

div.jp-block-label {
  text-align: center;
  font-family: "SimSun", "宋体", serif;
  font-size: 11px;
  color: #555555;
  margin: 14px auto 2px auto;
  page-break-after: avoid;
}
div.jp-legend {
  text-align: center;
  font-family: "SimSun", "宋体", serif;
  font-size: 10.5px;
  color: #444444;
  margin: 0 auto 10px auto;
}
div.jp-legend .jp-lg { margin: 0 7px; white-space: nowrap; }
div.jp-legend .jp-lg i {
  display: inline-block; width: 10px; height: 10px; margin-right: 4px;
  border: 1px solid; vertical-align: -1px;
}
""".replace("{fill}", DEFAULT_FILL).replace("{border}", DEFAULT_BORDER)

HTML_SHELL = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""


# ---------------------------------------------------------------- 术语表
def load_known_terms():
    path = os.path.join(HERE, "references", "grammar_terms.md")
    if not os.path.exists(path):
        return set()
    terms = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\|\s*([^|]+?)\s*\|", line)
            if m:
                t = m.group(1).strip()
                if t and not t.startswith("-") and t != "术语":
                    terms.add(t)
    return terms


def load_color_registry():
    """读 references/colors.md：角色/团队代表色注册表（可积累、可复用）。"""
    path = os.path.join(HERE, "references", "colors.md")
    if not os.path.exists(path):
        return {}
    reg = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\|\s*([^|]+?)\s*\|\s*(#[0-9a-fA-F]{3,8})\s*\|", line)
            if m:
                name = m.group(1).strip()
                if name and not name.startswith("-") and name != "名称":
                    reg[name] = m.group(2).lower()
    return reg


# ---------------------------------------------------------------- 渲染
def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_line(line, scheme, palette, block_color):
    words = line.get("words") or []
    if not words:
        return ""

    color = palette.resolve(line.get("singer"), block_color)
    color = color or palette.resolve(line.get("color"), block_color)
    cls = palette.css_class(color)

    romaji_row, kana_row, kanji_row, gram_row, gloss_row = [], [], [], [], []

    for w in words:
        kana = w.get("kana", "")
        kanji = w.get("kanji", kana)
        romaji = w.get("romaji") or word_romaji(kana, scheme=scheme)
        romaji_row.append('<td class="r-romaji">%s</td>' % esc(romaji))
        kana_row.append('<td class="r-kana">%s</td>' % esc(kana))
        kanji_row.append('<td class="r-kanji">%s</td>' % esc(kanji))
        gram_row.append('<td class="r-gram">%s</td>' % esc(w.get("grammar", "")))
        gloss_row.append('<td class="r-gloss">%s</td>' % esc(w.get("gloss", "")))

    ncol = len(words)
    rows = [
        "<tr>%s</tr>" % "".join(romaji_row),
        "<tr>%s</tr>" % "".join(kana_row),
        "<tr>%s</tr>" % "".join(kanji_row),
        "<tr>%s</tr>" % "".join(gram_row),
        "<tr>%s</tr>" % "".join(gloss_row),
    ]
    trans = line.get("trans", "")
    if trans:
        rows.append('<tr><td class="r-trans" colspan="%d">%s</td></tr>' % (ncol, esc(trans)))

    return '<table class="jp-line %s">%s</table>' % (cls, "".join(rows))


def render_header(data):
    """页首：居中曲名 + 其下小字信息栏（作詞/作曲/演唱者…）。"""
    parts = []
    title = data.get("title") or data.get("song")
    if title:
        parts.append('<div class="jp-title">%s</div>' % esc(title))

    meta = data.get("meta") or {}
    items = []
    if isinstance(meta, dict):
        for k, v in meta.items():
            items.append('<span class="jp-mi">%s：%s</span>' % (esc(k), esc(v)))
    elif isinstance(meta, list):
        for it in meta:
            if isinstance(it, dict):
                for k, v in it.items():
                    items.append('<span class="jp-mi">%s：%s</span>' % (esc(k), esc(v)))
            else:
                items.append('<span class="jp-mi">%s</span>' % esc(it))
    if items:
        parts.append('<div class="jp-meta">%s</div>' % "".join(items))
    return "".join(parts)


def render_block(block, scheme, show_labels, palette):
    block_color = palette.resolve(block.get("singer"), None) or \
        palette.resolve(block.get("color"), None)
    parts = []
    for raw in block.get("lines", []):
        html = render_line(raw, scheme, palette, block_color)
        if html:
            parts.append(html)
    if not parts:
        return ""
    head = ""
    if show_labels and block.get("id"):
        head = '<div class="jp-block-label">%s</div>' % esc(block["id"])
    return head + "\n".join(parts)


def build_html(data, scheme, show_labels, show_legend, show_title=True):
    scheme = data.get("scheme") or scheme
    palette = Palette(data.get("palette"), load_color_registry())

    by_id = {}
    for b in data.get("blocks", []):
        if b.get("id"):
            by_id[b["id"]] = b

    chunks = []
    for b in data.get("blocks", []):
        if b.get("ref"):
            src = by_id.get(b["ref"])
            if src is None:
                print("[WARN] 引用块 ref=%r 找不到对应 id，已跳过" % b["ref"])
                continue
            b = src
        html = render_block(b, scheme, show_labels, palette)
        if html:
            chunks.append(html)

    header = render_header(data) if show_title else ""
    legend = palette.legend_html() if show_legend else ""
    css = CSS + "\n" + palette.css_rules() + ("\n" + _legend_css() if show_legend else "")
    return HTML_SHELL.format(
        title=esc(data.get("title", "日语歌词分解表")),
        css=css,
        body=header + legend + "\n".join(chunks),
    )


def _legend_css():
    return ""


# ---------------------------------------------------------------- 校验
def check_data(data, known_terms):
    problems = []

    # 页首标题区是成品硬要求：居中曲名 + 其下居中信息栏
    title = data.get("title") or data.get("song")
    if not (isinstance(title, str) and title.strip()):
        problems.append("页首缺 title：成品开头必须有居中曲名（除了刻意用 --no-title）")
    meta = data.get("meta")
    has_meta = bool(meta) and (
        any(str(v).strip() for v in meta.values()) if isinstance(meta, dict)
        else bool([x for x in meta if x])
    )
    if not has_meta:
        problems.append("页首缺 meta：曲名下方需小字居中罗列作詞/作曲/歌等（顺序即书写顺序）")

    palette_names = set((data.get("palette") or {}).keys())
    for bi, b in enumerate(data.get("blocks", [])):
        if b.get("ref"):
            continue
        for li, ln in enumerate(b.get("lines", [])):
            tag = "%s#L%d" % (b.get("id", "block%d" % bi), li + 1)
            words = ln.get("words") or []
            if not words:
                problems.append("%s: 没有 words" % tag)
                continue
            sg = ln.get("singer")
            if sg and sg not in palette_names and not str(sg).startswith("#"):
                problems.append("%s: singer %r 不在 palette 里" % (tag, sg))
            for w in words:
                if not w.get("kana"):
                    problems.append("%s: 缺少 kana -> %r" % (tag, w.get("kanji")))
                g = w.get("grammar", "")
                if g and known_terms and g not in known_terms:
                    problems.append("%s: 语法术语不在术语表 -> %s" % (tag, g))
                gl = w.get("gloss", "")
                if gl and len(gl) > 6:
                    problems.append("%s: 词义超过 6 字 -> %s" % (tag, gl))
            if not ln.get("trans"):
                problems.append("%s: 缺整句翻译" % tag)

    for p in problems:
        print("  " + p)
    return len(problems)


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description="日语歌词逐词分解表生成器")
    ap.add_argument("--data", required=True, help="歌词数据 JSON")
    ap.add_argument("--out", help="输出 HTML 路径")
    ap.add_argument("--scheme", default="spec", choices=["spec", "hepburn"])
    ap.add_argument("--labels", action="store_true", help="显示段落标签（Aメロ/サビ…）")
    ap.add_argument("--legend", action="store_true", help="顶部渲染角色配色图例")
    ap.add_argument("--no-title", action="store_true", help="不输出页首曲名/信息栏")
    ap.add_argument("--check", action="store_true", help="只做数据体检")
    ap.add_argument("--palettes", action="store_true", help="打印配色推导结果")
    args = ap.parse_args()

    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)

    if args.palettes:
        for name, e in (data.get("palette") or {}).items():
            color = e.get("color") if isinstance(e, dict) else e
            fill, border = derive(color)
            print("%-8s %-9s base=%s  fill=%s  border=%s" % (name, "", color, fill, border))
        return 0

    known = load_known_terms()
    n = check_data(data, known)
    if n:
        print("[CHECK] %d 个待确认项（不阻断生成，仅为提示）" % n)
    else:
        print("[CHECK] 数据体检通过")

    if args.check:
        return 0 if n == 0 else 1

    if not args.out:
        print("[ERR] 需要 --out")
        return 2

    html = build_html(data, args.scheme, args.labels, args.legend, not args.no_title)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)

    nlines = html.count('<table class="jp-line')
    print("[OK] %s  -> %d 句表格，%d 字节" % (args.out, nlines, len(html.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
