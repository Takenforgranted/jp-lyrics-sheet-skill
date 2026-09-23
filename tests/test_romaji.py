# -*- coding: utf-8 -*-
"""罗马音规则回归测试：python tests/test_romaji.py"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from romaji import kana_to_romaji, word_romaji  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

CASES_SPEC = [
    ("おもいどおり", "o mo i do o ri"),
    ("いっそ", "i s so"),
    ("きっと", "ki t to"),
    ("ひきこもって", "hi ki ko mo t te"),
    ("まわってる", "ma wa t te ru"),
    ("どう", "do u"),            # 「う」长音，不是长音符
    ("どー", "do-"),             # 长音符「ー」并入前一假名
    ("ラブレター", "ra bu re ta-"),
    ("しょ", "syo"),
    ("しゃ", "sya"),
    ("しゅ", "syu"),
    ("ちゃ", "cha"),
    ("ちゅ", "chu"),
    ("ちょ", "cho"),
    ("ちょっと", "cho t to"),
    ("チャージ", "cha- zi"),
    ("じゃ", "zya"),
    ("じょ", "zyo"),
    ("ちぇ", "che"),
    ("にゃ", "nya"),
    ("ちきゅう", "chi kyu u"),
    ("ナンバーワン", "na n ba- wa n"),
    ("ファンタジー", "fa n ta zi-"),
    ("やおよろず", "ya o yo ro zu"),
    ("さがしてる", "sa ga si te ru"),
]

CASES_PARTICLE = [("は", "wa"), ("へ", "e"), ("を", "o")]

CASES_HEPBURN = [("し", "shi"), ("ふ", "fu"), ("じ", "ji"), ("しゃ", "sha")]


def run(cases, **kw):
    bad = 0
    for src, want in cases:
        got = word_romaji(src, **kw)
        if got != want:
            bad += 1
            print("FAIL %-10s got=%-24s want=%s" % (src, got, want))
    return bad


def main():
    bad = 0
    bad += run(CASES_SPEC, scheme="spec")
    bad += run(CASES_PARTICLE, scheme="spec")
    bad += run(CASES_HEPBURN, scheme="hepburn")

    # 非假名透传
    got = kana_to_romaji("NO.1")
    if "NO.1" not in got.replace(" ", ""):
        bad += 1
        print("FAIL 非假名透传: %s" % got)

    total = len(CASES_SPEC) + len(CASES_PARTICLE) + len(CASES_HEPBURN) + 1
    print("%d/%d 通过" % (total - bad, total))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
