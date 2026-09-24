r"""
打包前的脱敏自查（**只扫描、不改文件**，安全）

把 skill 目录里残留的「个人敏感信息」揪出来：写死的用户名路径、本机盘符路径、
密钥/口令、邮箱、QQ/手机号等。分享或打 zip 之前跑一遍，输出 CLEAN 才打包。

用法：
  python desensitize.py                       # 扫 skill 自身（推荐）
  python desensitize.py --dir <目录>           # 扫别的目录
  python desensitize.py --extend "(?i)公司名"  # 追加一条自定义规则（可重复）
  python desensitize.py --binaries             # 连 PDF/PNG 等二进制一起扫（严格规则）
  python desensitize.py --list                 # 只列出规则表

退出码：0 = CLEAN；1 = 有命中（需处理）；2 = 用法错误。

命中不自动改文件——**人工确认后再动手**，避免把正常的系统路径
（Program Files / Windows\Fonts）误删。
"""

import argparse
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SELF = os.path.basename(os.path.abspath(__file__))

# 扫描时要跳过的目录
# dist/ 是打包产物（里面是 zip、发布文案等派生文件，不是要发布出去的 skill 源码），
# 不跳过的话它会把打包现场的临时内容一起扫进来、把 CLEAN 判定搞脏。
SKIP_DIRS = {"_smoke", "__pycache__", ".git", ".workbuddy", ".venv", "node_modules", "dist"}

# 二进制素材（默认跳过；--binaries 时才用严格规则扫）
BINARY_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".zip", ".ttf", ".ttc", ".ico"}

# 允许出现的系统路径（非个人隐私），命中这些不算问题
ALLOW = [
    r"C:\\Program Files",
    r"C:\\Program Files \(x86\)",
    r"C:\\Windows\\Fonts",
    r"%LOCALAPPDATA%",
    r"%USERPROFILE%",
    r"%PROGRAMFILES%",
    r"\$env:USERPROFILE",
]

# (规则名, 正则, 说明)
RULES = [
    ("写死用户主目录",
     r"[A-Za-z]:\\+Users\\+(?!%|\$|\{|<)[^\\\s\"'，。,；;)]+",
     "改成 %USERPROFILE%\\… 或 $env:USERPROFILE\\…"),
    ("本机盘符路径",
     r"\b[D-Fd-f]:[\\/][^\s\"'，。,；;)]+",
     "输出/工作目录改成 <OUT_DIR> / <WORK_DIR> 占位符"),
    ("疑似密钥/口令",
     r"(?i)\b(api[_\-]?key|apikey|secret|passwd|password|access[_\-]?token|bearer)\b"
     r"\s*[:=]\s*['\"]?[A-Za-z0-9_\-\.]{8,}",
     "一律换成 <API_KEY> / <TOKEN>，真值不入库"),
    ("长串十六进制/Base64（疑似 token）",
     r"\b(?:[A-Za-z0-9+/]{40,}={0,2}|[0-9a-fA-F]{32,})\b",
     "确认是不是凭证；是就删掉"),
    ("邮箱",
     r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
     "个人邮箱换成 <EMAIL>"),
    ("QQ / 手机号",
     r"(?<!\d)(?:[1-9]\d{4,10}@qq\.com|1[3-9]\d{9})(?!\d)",
     "确认是否是个人号码"),
    ("主机名 / 账户名", r"(?i)\bLenovo\b|\bDESKTOP-[A-Z0-9]+\b|\bLAPTOP-[A-Z0-9]+\b",
     "换成占位符（主机名/账户名）"),
    ("绝对工作区路径", r"[A-Za-z]:\\+WorkBuddy\\+", "换成 <WORK_DIR>"),
]

# 二进制只查这几条（避免把 PDF 内部数据流当凭证误报）
STRICT_NAMES = {"写死用户主目录", "邮箱", "主机名 / 账户名", "绝对工作区路径", "本机盘符路径"}


def is_allowed(line):
    return any(re.search(a, line) for a in ALLOW)


def scan_text(text, rules):
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if is_allowed(line):
            continue
        for name, pat, _hint in rules:
            for m in re.finditer(pat, line):
                hits.append((i, name, m.group(0)[:80]))
    return hits


def scan_binary(path, rules):
    """二进制按可打印串扫，只报严格规则。"""
    try:
        raw = open(path, "rb").read()
    except OSError:
        return []
    hits = []
    for m in re.finditer(rb"[\x20-\x7e]{6,}", raw):
        s = m.group(0).decode("ascii", "replace")
        if is_allowed(s):
            continue
        for name, pat, _hint in rules:
            for mm in re.finditer(pat, s):
                hits.append((m.start(), name, mm.group(0)[:80]))
    return hits


def main():
    ap = argparse.ArgumentParser(description="打包前脱敏自查（只扫描）")
    ap.add_argument("--dir", default=SKILL, help="要扫描的目录，默认本 skill")
    ap.add_argument("--extend", action="append", default=[],
                    help="追加正则规则，可重复；写成 '(?i)关键字'")
    ap.add_argument("--binaries", action="store_true",
                    help="连 PDF/PNG 等二进制一起扫（只报严格规则）")
    ap.add_argument("--list", action="store_true", help="只打印规则表")
    args = ap.parse_args()

    if args.list:
        for name, pat, hint in RULES:
            print("%-16s %-58s %s" % (name, pat, hint))
        return 0

    rules = list(RULES)
    for i, p in enumerate(args.extend, 1):
        try:
            re.compile(p)
        except re.error as e:
            print("[ERR] --extend 第 %d 条正则不合法：%s" % (i, e))
            return 2
        rules.append(("自定义#%d" % i, p, "自定义规则"))
    bin_rules = [r for r in rules if r[0] in STRICT_NAMES or r[0].startswith("自定义")]

    root = os.path.abspath(args.dir)
    if not os.path.isdir(root):
        print("[ERR] 目录不存在：%s" % root)
        return 2

    scanned_text, scanned_bin, total = 0, 0, 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            if fn == SELF:          # 规则表自己必然命中自己，跳过
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root)
            ext = os.path.splitext(fn)[1].lower()
            if ext in BINARY_EXT:
                if not args.binaries:
                    continue
                scanned_bin += 1
                hits = scan_binary(p, bin_rules)
                where = "@"
            else:
                try:
                    with open(p, "r", encoding="utf-8", errors="replace") as f:
                        text = f.read()
                except OSError:
                    continue
                scanned_text += 1
                hits = scan_text(text, rules)
                where = "L"
            if hits:
                print("\n[命中] %s" % rel)
                for line, name, got in hits:
                    print("   %s%-6d %-16s %s" % (where, line, name, got))
                total += len(hits)

    print("\n扫描 %d 个文本%s，命中 %d 处"
          % (scanned_text, " + %d 个二进制" % scanned_bin if scanned_bin else "", total))
    if total:
        print("结论: DIRTY —— 按上表逐条处理（占位符写法见 SKILL.md「脱敏约定」）")
        return 1
    print("结论: CLEAN —— 可以打包")
    return 0


if __name__ == "__main__":
    sys.exit(main())
