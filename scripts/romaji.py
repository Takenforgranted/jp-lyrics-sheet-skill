# -*- coding: utf-8 -*-
"""
假名 -> 罗马音转换（jp-lyrics-sheet 专用方案）

遵循 SKILL.md 的罗马音约定：
  * 逐假名空格分隔
  * し=si / ち=chi / つ=tsu / ふ=hu / じ=zi（spec 方案，与参考 PDF 一致）
  * 拗音：しょ=syo じょ=zyo じゃ=zya ちぇ=che ...
  * 长音符「ー」并入前一假名，写作 kyo- / do- / o-
  * 促音「っ」双写后一假名的辅音：って -> t te，きっと -> ki t to，いっそ -> i s so
  * 助词 は=wa、へ=e、を=o（仅当单假名成栏时生效，可用 particle=False 关闭）

另提供 hepburn 方案（し=shi / ふ=fu / じ=ji / しゃ=sha），用 scheme="hepburn" 切换。

CLI:
  python romaji.py "思い通り" "逃げ込める" --scheme spec
"""

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ---------------------------------------------------------------- 五十音表
_SPEC = {
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "さ": "sa", "し": "si", "す": "su", "せ": "se", "そ": "so",
    "た": "ta", "ち": "chi", "つ": "tsu", "て": "te", "と": "to",
    "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "hi", "ふ": "hu", "へ": "he", "ほ": "ho",
    "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "や": "ya", "ゆ": "yu", "よ": "yo",
    "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro",
    "わ": "wa", "を": "o", "ん": "n",
    "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go",
    "ざ": "za", "じ": "zi", "ず": "zu", "ぜ": "ze", "ぞ": "zo",
    "だ": "da", "ぢ": "zi", "づ": "zu", "で": "de", "ど": "do",
    "ば": "ba", "び": "bi", "ぶ": "bu", "べ": "be", "ぼ": "bo",
    "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po",
    "ゔ": "vu",
}

# hepburn 与 spec 的差异项（其余全部相同）
_HEPBURN_DELTA = {"し": "shi", "ふ": "fu", "じ": "ji", "ぢ": "ji"}

# 拗音 / 外来音节特例（优先于一般规则）
_COMBO = {
    ("ふ", "ぁ"): "fa", ("ふ", "ぃ"): "fi", ("ふ", "ぇ"): "fe",
    ("ふ", "ぉ"): "fo", ("ふ", "ゅ"): "fyu",
    ("う", "ぃ"): "wi", ("う", "ぇ"): "we", ("う", "ぉ"): "wo",
    ("ゔ", "ぁ"): "va", ("ゔ", "ぃ"): "vi", ("ゔ", "ぇ"): "ve",
    ("ゔ", "ぉ"): "vo", ("ゔ", "ゅ"): "vyu",
    ("て", "ぃ"): "ti", ("て", "ゅ"): "tyu",
    ("で", "ぃ"): "di", ("で", "ゅ"): "dyu",
    ("ち", "ぇ"): "che", ("し", "ぇ"): "she", ("じ", "ぇ"): "je",
    ("す", "ぃ"): "si", ("ず", "ぃ"): "zi",
    ("つ", "ぁ"): "tsa", ("つ", "ぉ"): "tso",
}

_SMALL = {
    "ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o",
    "ゃ": "ya", "ゅ": "yu", "ょ": "yo", "ゎ": "wa",
}
_Y = {"ゃ": "a", "ゅ": "u", "ょ": "o"}

# 促音后继辅音（不能简单 rstrip 元音的那些）
_SOKUON = {"chi": "t", "tsu": "t", "shi": "s", "si": "s",
           "ji": "z", "zi": "z", "hu": "h", "fu": "f"}

_PARTICLE = {"は": "wa", "へ": "e", "を": "o"}


# ---------------------------------------------------------------- 工具
def _to_hira(ch):
    """片假名 -> 平假名，其他原样返回。"""
    o = ord(ch)
    if 0x30A1 <= o <= 0x30F6:
        return chr(o - 0x60)
    return ch


def _table(scheme="spec"):
    t = dict(_SPEC)
    if scheme == "hepburn":
        t.update(_HEPBURN_DELTA)
    elif scheme != "spec":
        raise ValueError("scheme 只能是 'spec' 或 'hepburn'")
    return t


def _consonant(base):
    """ka -> k, chi -> ch, si -> s"""
    return base.rstrip("aeiou") or base


def _initial_consonant(kana, table):
    """促音后继辅音：って -> t，いっそ -> s"""
    r = table.get(kana)
    if not r:
        return "t"
    if r in _SOKUON:
        return _SOKUON[r]
    return _consonant(r) or "t"


def _palatal(base, v, scheme):
    """拗音：ki + ゃ -> kya；si + ょ -> syo（spec）/ sho（hepburn）；chi + ゃ -> cha"""
    if base in ("si", "shi"):
        return ("s" + "y" + v) if scheme == "spec" else ("sh" + v)
    if base in ("zi", "ji"):
        return ("z" + "y" + v) if scheme == "spec" else ("j" + v)
    if base == "chi":            # ちゃ/ちゅ/ちょ -> cha/chu/cho（不是 chya）
        return "ch" + v
    return _consonant(base) + "y" + v


# ---------------------------------------------------------------- 主函数
def kana_to_romaji(text, scheme="spec"):
    """把假名串转成按假名空格分隔的罗马音（返回 str）。"""
    table = _table(scheme)
    out, i, n = [], 0, len(text)
    while i < n:
        ch = _to_hira(text[i])

        # 长音符：并入前一个假名
        if ch == "ー":
            if out and not out[-1].endswith("-"):
                out[-1] = out[-1] + "-"
            else:
                out.append("-")
            i += 1
            continue

        # 促音：输出后继辅音
        if ch in ("っ", "ッ"):
            nxt = _to_hira(text[i + 1]) if i + 1 < n else ""
            out.append(_initial_consonant(nxt, table))
            i += 1
            continue

        # 独立小写假名
        if ch in _SMALL and ch not in table:
            out.append(_SMALL[ch])
            i += 1
            continue

        base = table.get(ch)
        if base is None:          # 非假名（汉字 / 标点 / 数字）原样透传
            if text[i].strip():   # 空白只作分隔，不产生 token
                out.append(text[i])
            i += 1
            continue

        # 拗音 / 外来音节
        if i + 1 < n:
            nx = _to_hira(text[i + 1])
            if nx in _SMALL:
                key = (ch, nx)
                if key in _COMBO:
                    out.append(_COMBO[key])
                elif nx in _Y:
                    out.append(_palatal(base, _Y[nx], scheme))
                else:
                    out.append(_consonant(base) + _SMALL[nx])
                i += 2
                continue

        out.append(base)
        i += 1

    return " ".join(out)


def word_romaji(kana, scheme="spec", particle=True):
    """单词级罗马音：额外处理单假名助词（は->wa / へ->e / を->o）。"""
    if not kana:
        return ""
    if particle and len(kana) == 1:
        h = _to_hira(kana)
        if h in _PARTICLE:
            return _PARTICLE[h]
    return kana_to_romaji(kana, scheme=scheme)


# ---------------------------------------------------------------- CLI
if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    scheme = "hepburn" if "--hepburn" in sys.argv else "spec"
    if not args:
        print(__doc__)
        sys.exit(0)
    for a in args:
        print("%-14s -> %s" % (a, word_romaji(a, scheme=scheme)))
