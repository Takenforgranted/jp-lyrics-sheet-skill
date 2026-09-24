---
name: jp-lyrics-sheet
version: 1.0.0
author: Takenforgranted
display_name: 日语歌词逐词分解表
display_name_en: Japanese Lyrics Word-by-Word Sheet
category: education
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch, WebFetch
description: |-
  把一首日文歌做成《神のまにまに》同款逐词分解表：每句一组表格，逐词一列，六行自上而下为 罗马音 / 假名 / 写法 / 语法标注 / 词义 / 整句翻译，成品为可直接打印的 A4 PDF（HTML 同步产出）。自带假名→罗马音引擎、角色配色推导与 HTML→PDF 工具链，数据驱动，换歌只改 JSON。开源仓库：https://github.com/Takenforgranted/jp-lyrics-sheet-skill

  Use when 用户要求做日语歌词分解、歌词笔记、逐词翻译表，或提到「歌词表」「Sheet 样式」「假名罗马音对照」并要求输出表格 / PDF。
description_zh: |-
  输入一首日文歌，产出《神のまにまに》同款逐词六行分解表（罗马音 → 假名 → 写法 → 语法 → 词义 → 整句翻译），一句一组表格，成品是可打印的 A4 PDF，同时输出自包含 HTML。自带假名→罗马音引擎（spec / hepburn 双方案，处理促音、长音、拗音与助词 は/へ/を）、角色配色（填充 / 边框 / 字色由代表色自动推导，字色强制对底色保持 WCAG ≥ 7:1 可读）、以及 doctor / cleanup / desensitize / pack 四个辅助脚本。数据驱动，换一首歌只改 JSON；依赖 Windows 系统字体（MS Mincho / 宋体）与 Chrome 或 Edge。开源仓库：https://github.com/Takenforgranted/jp-lyrics-sheet-skill
description_en: |-
  Turn a Japanese song into a word-by-word annotation sheet: each lyric line becomes one table with six rows — romaji, kana, original writing, grammar tag, gloss, full-line translation — exported as a print-ready A4 PDF (self-contained HTML in the same run). Ships with a built-in kana-to-romaji engine (spec / hepburn schemes; handles sokuon, long vowels, yoon and the particles は/へ/を), per-singer palettes (fill / border / text auto-derived from each artist colour, text contrast forced to WCAG >= 7:1 against the fill) and four helper scripts (doctor / cleanup / desensitize / pack). Fully data-driven: a new song only means a new JSON file. Requires Windows system fonts and Chrome or Edge. Open-source repo: https://github.com/Takenforgranted/jp-lyrics-sheet-skill
examples:
  - "把《光るなら》做成歌词逐词分解表，输出 PDF"
  - "这首日文歌做一版带角色配色的逐词表"
  - "给这段歌词做逐词语法标注和翻译对照表"
agent_created: true
---

# 日语歌词逐词分解表工作流

本 skill 面向「歌词翻译 / 逐词笔记」这类反复使用的场景。成品样式参照《神のまにまに》参考版
（`assets/sample_kaminomanimani.pdf` / `.png`，既是样式基准也是能跑通的样例，
**已含页首标题区**：居中曲名 + 其下小字信息栏）。

**本 skill 自带完整工具链，不依赖外部模板脚本。** 任何机器装好后先跑
`doctor.py`，PASS 就可以直接开工。

## 出处 / 致谢 / 许可

- **开源仓库**：<https://github.com/Takenforgranted/jp-lyrics-sheet-skill>（public，自由使用 / 改进，欢迎 issue 与 PR）。
- **原始作者：YJY**。这套「逐词六行分解表」的样式基准（粉底表格、六行字段排布）、JSON 数据结构与最初的工作流
  都出自 YJY 的原始作品；本仓库是在其基础上做整理、修复与工具链补齐（浏览器自动探测、页首标题区固化、
  角色配色推导、`doctor` / `cleanup` / `desensitize` / `pack`），功劳的起点属于 YJY。
- **免责声明**：本 skill 只负责排版，**不提供歌词数据**；产出的歌词与翻译著作权归各自权利人，
  仅供个人学习与歌词笔记使用，请勿用于商业用途或整曲公开传播。

## 目录结构

```
jp-lyrics-sheet/
├── SKILL.md                          ← 本文件
├── scripts/
│   ├── romaji.py                     假名→罗马音引擎（含促音/长音/助词规则）
│   ├── gen_sheet.py                  JSON → HTML 渲染器（含页首标题区；样式都在 CSS 常量里）
│   ├── build.py                      HTML → PDF（浏览器自动探测）+ 品牌图标盖章 + 渲 PNG 目检
│   ├── doctor.py                     环境自检（--smoke 跑端到端，含页首标题区/品牌图标断言）
│   ├── cleanup.py                    ★ 收尾清理中间文件（默认 dry-run）
│   ├── desensitize.py                ★ 打包前脱敏自查（只扫描不改文件）
│   └── pack.py                       ★ 打包 zip（--verify 顺带跑解压副本自检）
├── references/
│   ├── grammar_terms.md              语法术语表（--check 拿它校验数据）
│   └── colors.md                     角色/团队代表色注册表（自动加载、可积累）
├── assets/
│   ├── icon.png                      品牌图标（build.py 盖章到 PDF 每页右上角）
│   ├── sample_kaminomanimani.json    样例数据（Aメロ+サビ 7 句，可直接跑）
│   ├── sample_kaminomanimani.pdf     参考成品（样式基准，含页首标题区；与 .json 同名）
│   ├── sample_kaminomanimani.png     参考成品预览图
│   ├── sample_mix_shake.json         角色配色完整示例（スリーズブーケ《Mix shake!!》全曲 46 句）
│   ├── sample_hikaru_nara.json       长曲全曲示例（《光るなら》27 句，演示 `ref` 复用副歌）
│   ├── sample_sora_no_hako.json      单一「乐队主题色」示例（トゲナシトゲアリ《空の箱》全曲 39 句，
│   │                                 配 `--legend --labels`；也是字色随底色推导的实测样例）
├── examples/                         ★ 示例成果：《Mix shake!!》色彩版、《空の箱》单色版（PDF/HTML + 预览图）
└── tests/
    └── test_romaji.py                罗马音规则回归测试
```

> **目录层级硬约束（上架平台要求）**：包内**最多两级目录**（`scripts/`、`references/`、`assets/`、
> `tests/`、`examples/` 下**不许再建子目录**）。三级路径（如曾经的 `assets/reference/x.pdf`）会被
> 开放平台判为「目录层级超限」直接拒收，已扁平化为 `assets/sample_kaminomanimani.pdf`。
> 新增资源前先想清楚：放不进二级目录就换命名前缀，别建第三层。

## 样式规格（已固化在 `gen_sheet.py` 的 CSS 常量里，别手抄）

- 每句一组 `<table class="jp-line">`，逐词一列，六行从上到下：
  1. **罗马音** `.r-romaji`：Times New Roman 10.5px，小写
  2. **假名** `.r-kana`：MS Mincho 11.5px（全平假名写法，外来语保留片假名）
  3. **写法** `.r-kanji`：MS Mincho 13.5px（歌词原文，含汉字）
  4. **语法标注** `.r-gram`：宋体 10.5px，中文术语
  5. **词义** `.r-gloss`：宋体 12px，2–6 字短注释
  6. **整句翻译** `.r-trans`：colspan=全列，宋体 12px，字距 .08em
- 单元格：背景 `#f3d7d7`，边框 1px `#6e3636`，padding 3px 7px，居中，nowrap
- 表格居中，间距 11px；A4 竖版 `@page{size:A4;margin:14mm 10mm}`，
  `page-break-inside:avoid`，`print-color-adjust:exact`（保证粉色底不丢）
- **页首标题区（硬要求，见下节）**：居中曲名 + 其下小字居中信息栏
- **角色配色**：`--legend` 顶部渲图例；块/行可指定 `singer`，填充/边框/**字色**三色由代表色 HSL 推导（见下）
- **品牌图标（PDF 硬要求，见下节）**：`build.py` 把 `assets/icon.png` 盖章到每页右上角
- 无页眉页脚，纯白背景

要改样式只改 `gen_sheet.py` 里的 `CSS` 常量，改完全跑 `doctor.py --smoke` 目检。

## 页首标题区（成品硬要求，HTML 与 PDF 都要有）

**任何一次生成的 HTML / PDF，正文开头都必须先是标题区，再接表格。** 结构固定两层：

1. **曲名**：整行**居中**（`div.jp-title`，MS Mincho 19px，字距 `.06em`，深灰 `#232323`）。
   **只放曲名**——歌手、作词、收录专辑这类信息不许塞进曲名行。
2. **信息栏**：紧随其下、同样**居中**的一行**小字**（`div.jp-meta`，宋体 10.5px，
   `#666`，行高 1.7），按书写顺序罗列**作詞 / 作曲 / 編曲 / 歌 / Center / 収録** 等。
   每项渲成「键：值」，项间自动留白（`margin: 0 8px`），超宽自动换行，整块始终居中。

数据侧只填两个字段（顺序即显示顺序，dict 保序）：

```json
{
  "title": "Mix shake!!",
  "meta": {
    "歌": "スリーズブーケ（日野下花帆・乙宗梢）",
    "作詞": "ケリー",
    "作曲・編曲": "川崎智哉",
    "収録": "1st シングル《Reflection in the mirror》"
  }
}
```

- 生成位置：`render_header()` 写在 `build_html()` 里，**渲染在 legend 和所有表格之前**，
  两块都带 `page-break-after: avoid`，不会被挤到下一页跟表格分家。
- `--check` 会在缺 `title` 或 `meta` 时给出提示（不阻断生成，但应当补上）。
- `doctor.py --smoke` 会断言样例产物开头确实有 `jp-title` / `jp-meta`，缺了直接 FAIL。
- 只有做「续页 / 局部片段」才可以加 `--no-title` 关掉；常规成品**不要关**。
- 想换曲名的字体/字号/颜色，改 `CSS` 里的 `div.jp-title` / `div.jp-meta` 两处即可。

## 页眉品牌图标（PDF 硬要求，每页右上角）

**任何一次导出的 PDF，每一页右上角都必须有 skill 图标（`assets/icon.png`）。**
实现放在 `build.py` 的 `stamp_brand()`：Chrome 打印完成后，用 PyMuPDF 把图标
（24pt ≈ 8.5mm 见方）插到**纸面**右上角——上边距 14mm × 右边距 10mm 的交角里，
与正文版面物理隔离，**任何页、任何内容都压不到**，HTML 与分页完全不受影响。

- 每页都盖（`for page in doc`），成品三例（1/6/6 页）已逐页像素验证。
- `--no-brand` 可关（仅续页/局部片段用）；图标文件缺失或 PyMuPDF 未装时**跳过并警告**，不让导出失败。
- 依赖：`pip install pymupdf`（可选；只影响盖章，不影响 PDF 本体导出）。
- `doctor.py --smoke` 会渲出 sample.pdf 第 1 页做**像素断言**：右上角扫不到图标直接 FAIL。
- **别用 CSS `position:fixed` 在 HTML 里实现这个需求**——Chrome 打印对 fixed 元素的
  负偏移有怪癖：负 top 会被挪到右下角且只出现一次、负 right 直接被裁掉、
  `transform: translateY` 同样翻车；正偏移（top:0）虽能逐页重复，但会压到宽信息栏。
  盖章方案绕开全部这些坑。

## 角色配色（独唱/合唱分色）

用户要求不同角色的段落表格用不同代表色。已在 `gen_sheet.py` 实现：

- **代表色注册表** `references/colors.md` —— `gen_sheet.py` 自动加载。数据 JSON 里写
  `"singer": "日野下花帆"` 即可直接命中，无需手写 palette。新角色核实后**登记进这张表**。
- 数据里也可临时 `"palette": {"花帆": {"color": "#f8b500", "label": "日野下花帆"}}`，
  同名条目会覆盖注册表。
- **色值推导**（HSL）：填充 = 同色相同饱和、亮度 90%；边框 = 同色相、亮度 32%
  （饱和上限 0.85）；**字色 = 同色相、亮度 24% 起逐级压暗（饱和上限 0.75），
  直到对填充色的 WCAG 对比度 ≥ 7:1**，够不到就退化为纯黑/纯白里对比度更高的那个。
  未指定 `singer` 时沿用参考版固定粉（填充 `#f3d7d7` / 边框 `#6e3636`，字色不覆盖即默认黑）。
- **用户说「字色要适配底色 / 保证可读性」时**，就是上面第三条在起作用：不用手写颜色，
  底色偏浅（黄・青）或偏深都不会糊。核对该曲实际推导结果用 `--palettes`（会打印对比度）。
- 指定层级：块级 `"singer"` → 行级 `"singer"` 覆盖块级 → 都没有则默认粉。
  行内多人接唱时，该行颜色取**首段**歌手（萌百页面也是这么标色的）。
- `--legend` 会在顶部渲一行图例（色块 + 角色名），配色版必加。
- `--palettes` 可打印本曲所有配色的 base/fill/border 推导结果，便于核对。

代表色来源核实方法（萌百 `action=raw` 和 `api.php` 都被禁，只能抓渲染 HTML）：

1. `requests` 抓 `https://zh.moegirl.org.cn/<页面名>`（带浏览器 UA）
2. 统计页面里出现频率最高的 `#rrggbb` —— 角色页 top1 就是其代表色；
   歌曲页则解析 `<span style="color:...">`，**图例行即「颜色 ↔ 角色」权威映射**
3. 核实过就登记进 `references/colors.md`

参考实现（含配色 + 全曲 46 句）：`assets/sample_mix_shake.json`。

## 工作流

### 1. 环境自检（新机器第一次必跑）

```
& "$env:USERPROFILE\.workbuddy\binaries\python\envs\default\Scripts\python.exe" `
  "$env:USERPROFILE\.workbuddy\skills\jp-lyrics-sheet\scripts\doctor.py" --smoke
```

结论 `PASS` 即环境就绪（浏览器 / 字体 / 依赖 / 罗马音规则 / **页首标题区** / 端到端全查）。

### 2. 取词

uta-net（`/global/en/` 版可顺带拿罗马音）／kashinavi／官方歌词页**交叉核对**日文原文。
搜索时带上「歌詞 全文 歌手名」，中文翻译可用公众号译本或 Baidu 百科歌词区对照。

### 3. 分词并写 JSON

数据驱动，schema 见 `gen_sheet.py` 顶部 docstring，样例见
`assets/sample_kaminomanimani.json`。要点：

- **先填页首**：`title`（曲名，居中显示）＋ `meta`（作詞/作曲/編曲/歌/収録 等，
  小字居中罗列，键序＝显示顺序）。这是**硬要求**，漏了 `--check` 会提示、
  成品的 HTML/PDF 开头就会缺标题区。详见「页首标题区」一节。
- **按语素切栏**；助词（の・が・を・に・は・へ・と・も・や・から・って…）单独成栏
- 必填 `kana`（全平假名）；`kanji` 默认取 `kana`，有汉字务必写
- `romaji` 一般**不填**，让 `romaji.py` 自动生成；自动结果不对时才手写覆盖
- 助词 `は/へ/を` 单独成栏时会自动转 `wa/e/o`（在 `word_romaji` 里处理）
- 英文唱词整句一栏，`kana` 写片假名读法，`grammar:"英文"`
- **重复副歌段落**：先出现的块给 `"id": "サビ"`，后面重复处只写 `{"ref": "サビ"}`
  ——数据只维护一份，`build_html` 会自动展开
- 段落标签（Aメロ/サビ…）只在加 `--labels` 时才渲染，默认纯表格

### 4. 罗马音方案（`romaji.py` 已实现，勿手算）

- 逐假名空格分隔；し=si、ち=chi、つ=tsu、ふ=hu、じ=zi（**spec 方案，与参考 PDF 一致**）
- 拗音：しょ=syo、じゃ=zya、ちぇ=che、にゃ=nya
- 长音符「ー」并入前一假名：`kyo-`、`do-`、`ta-`；**注意「どう」是 ど+う → `do u`，不是 `do-`**
- 促音双写后继辅音：って→`t te`、きっと→`ki t to`、いっそ→`i s so`
- を→o、へ→e、は→wa（助词时）
- 要 Hepburn（し=shi/しゃ=sha/じゃ=ja）时加 `--scheme hepburn` 或在 JSON 里写 `"scheme":"hepburn"`
- 改规则后必须跑 `python tests/test_romaji.py` 回归

### 5. 生成 HTML + PDF

```
gen_sheet.py --data song.json --out song.html --check     # --check 只体检不产出
gen_sheet.py --data song.json --out song.html --legend    # 角色配色版
build.py song.html                                        # 产 song.pdf + 前 3 页预览 PNG
```

`build.py` 按序自动探测：Chrome → Edge → Playwright chromium，全都没有才报错。

### 6. 校验后交付

用 `build.py` 渲出的 PNG **目检**——**先看第一页有没有居中曲名 + 小字信息栏**，
再看字体、断行、配色、翻译行。确认无误后 `present_files`：**PDF 在前，HTML 随后**。

想要个「好看长什么样」的参照，直接看 `examples/Mix_Shake!!_歌词分解表.pdf`
（全曲 46 句、角色配色版、6 页，`examples/mix_shake_p1.png` 是第 1 页预览图）；
单主题色 + 字色随底色推导的参照看 `examples/空の箱_逐词分解表.pdf`（全曲 39 句、`--labels`）。

### 7. 收尾清理（必做，交付完立刻跑）

生成过程会在工作区堆一堆中间产物——抓下来的网页 dump、解析中间文件、一次性脚本、
日志、渲染预览 PNG，以及 Chrome 无头打印留在 `%TEMP%` 的 `jpsheet_*` profile 目录。
**交付完成后必须清掉**，别把垃圾留在工作区。

```
cleanup.py --work-dir . --keep out.pdf,out.html            # 先预演，看清单
cleanup.py --work-dir . --keep out.pdf,out.html --apply    # 确认后真删
cleanup.py --work-dir . --apply --temp --skill             # 连 %TEMP% 残留和 skill 内部缓存一起清
```

清理规则（已固化在 `cleanup.py`，保守优先）：

- **默认 dry-run**，加 `--apply` 才真删；**先跑预演看清单**再执行。
- 只删**白名单模式**命中的东西（`FILE_PATTERNS` / `DIR_PATTERNS`），
  绝不做「除了成品都删」式的通配删除。要覆盖新类型就往白名单里加。
- **永远保留**：`--keep` 指定的成品、源数据 `*.json`（除非加 `--include-data`）、
  `.workbuddy/`、`.git/`、以及 skill 自己的 `scripts/ references/ assets/ SKILL.md`。
- 常用参数：`--temp` 清 `%TEMP%\jpsheet_*`（Chrome 临时 profile，量大且隐蔽）、
  `--skill` 清 skill 内部 `_smoke/` 与 `__pycache__`、`--recursive` 递归子目录、
  `--pattern "verify*.txt,dbg*.txt"` 追加一次性残留的模式（白名单覆盖不到的临时文件用它）。
- 好的样例数据 JSON **不要删**——有价值的话先拷进 `assets/`（如 `sample_mix_shake.json`），
  再从工作区清掉。

### 8. 打包分享（要发 zip 时）

打包是「整包分享」，顺序不能颠倒，否则会把隐私或垃圾一起带出去：

1. 脱敏自查必须 **CLEAN**：`desensitize.py --binaries`（见「脱敏约定」）
2. 清内部缓存与临时残留：`cleanup.py --skill --apply` + `cleanup.py --work-dir <WORK_DIR> --apply --temp`
3. 打 zip：整包**平铺**（`SKILL.md`、`scripts/`、`references/`、`assets/`、`tests/` 直接在根，
   不套一层同名文件夹），**不带** `_smoke/`、`__pycache__`、`*.bak`

用 skill 自带的 `pack.py` 一步搞定（用 Python `zipfile`，比 `Compress-Archive` 可控；
后者在本机曾直接 exit 1 且无输出，别当唯一手段）：

```
%VENV_PYTHON% scripts/pack.py --out <OUT_DIR>\jp-lyrics-sheet.zip            # 只打包 + 校验完整性
%VENV_PYTHON% scripts/pack.py --out <OUT_DIR>\jp-lyrics-sheet.zip --verify   # 追加解压副本自检
```

`--verify` 会把 zip 解到临时目录（跑完自动删），在**解压副本**里依次跑
`doctor.py --smoke` + `tests/test_romaji.py` + `desensitize.py`，三项全绿才算这个包能用。

**要上架 WorkBuddy 技能市场（SkillHub）时结构不同**：包内顶层必须是 `jp-lyrics-sheet/`（不是平铺），
且**目录最多两级**（`assets/` 下不许再有子目录，三级路径会被平台判「目录层级超限」拒收）。
用发布流程 skill 的脚本打：

```
%VENV_PYTHON% ~/.workbuddy/skills/workbuddy-skill-publish/scripts/pack_market.py <本目录> \
    --name jp-lyrics-sheet --verify
```

## 坑（都是踩过的）

- **`--print-to-pdf` 的值在 subprocess 列表传参时不能带引号**：写成
  `'--print-to-pdf="C:\x.pdf"'` 会让 Chrome 把引号当文件名一部分，报
  `0x7B 文件名、目录名或卷标语法不正确`。只有 PowerShell 手敲时才靠 shell 剥引号。
- **Chrome 打印对 `position:fixed` 的负偏移有怪癖**（做每页页眉/水印时必踩）：
  负 top → 元素跑到**右下角**且只有第 1 页有；负 right → 直接被裁掉；
  transform 位移同样翻车。要在每页固定位置放东西，用 PDF 后处理盖章
  （`build.py` 的 `stamp_brand()`），别指望 CSS。
- 原 SKILL.md 写死的 Edge 路径在只有 Chrome 的机器上直接失效 → 一律走 `build.py` 自动探测。
- PDF 无文字层时用 pypdfium2 渲成 PNG 再读图，不要只靠 pypdf 抽文本。
- PowerShell 管道传日文脚本易乱码：一律用 Write 工具写 `.py`/`.json` 文件再执行；
  调 python 时加 `-X utf8`。
- 文件名避免 `∞` 等特殊字符。
- `--check` 的术语校验只提示不阻断；表外术语先补进 `references/grammar_terms.md` 再用。
- **Windows 上 shell 工具可能半残**：`Bash` 工具里 `ls`/`head`/`dirname` 等外部命令会报
  `command not found`（PortableGit 缺 coreutils），`PowerShell` 工具有时调用成功却不回传 stdout。
  → 文件/目录操作（列目录、复制、删成品副本、批量渲图）一律改用本机 venv python 的 `-c` 内联
  脚本，稳定可靠；也**不要**从 Bash 去调 PowerShell，会被安全策略直接拦掉。
- 成品文件名可以用日文/中文（`光るなら_逐词分解表.pdf` 实测通过 Chrome 打印），
  但**工作目录里的中间产物一律用 ASCII 名**（`hikaru_nara.json`），少一类编码坑。
- 「同曲不同源歌词有分歧」是常态：`悲しみを笑顔に` vs `も`、`消えないよ` vs `よう`、
  `忘れる` vs `薄れる` 都真实存在。**以 kashinavi + marumaru（后者注明了取自 uta-net）
  两源一致为准**，不要拿英文罗马音转写站反推日文原文。

## 脱敏约定（改本 skill / 打包前必须遵守）

分享 / 打包本 skill 前，所有**个人敏感信息**一律用占位符代替，不许写死真值：

| 类别 | 写法 |
| --- | --- |
| 用户主目录 | `$env:USERPROFILE\...` 或 `%USERPROFILE%\...`，**不写** `C:\Users\<真实用户名>\` |
| 本机专用盘符路径 | `%LOCALAPPDATA%\...` 这类环境变量；输出/工作目录写 `<OUT_DIR>` / `<WORK_DIR>` |
| Python 解释器 | 写 `$env:USERPROFILE\.workbuddy\...\python.exe`（相对主目录，**不含真实用户名**）；跨机器引用一律 `%VENV_PYTHON%` |
| API key / token / 密码 | 一律 `<API_KEY>` / `<TOKEN>`，**绝不入库** |
| 主机名 / 账户名 / 邮箱 / QQ | 一律 `<HOST>` / `<USER>` / `<EMAIL>` |
| 浏览器、字体等系统路径 | 保留（`C:\Program Files\...`、`C:\Windows\Fonts\...` 非个人隐私） |

**代码里的硬性要求**：需要用户目录时只用环境变量（`os.path.expandvars(r"%LOCALAPPDATA%\...")`、
`$env:USERPROFILE`），不要拼 `os.environ["USERNAME"]` 去凑 `C:\Users\<name>`——`build.py`
的浏览器探测就是这么写的。

自查（**只扫描不改文件**，输出 `CLEAN` 才能打包）：

```
%VENV_PYTHON% scripts/desensitize.py              # 扫 skill 自身（文本）
%VENV_PYTHON% scripts/desensitize.py --binaries   # 连 PDF/PNG 等二进制一起扫
%VENV_PYTHON% scripts/desensitize.py --list       # 看规则表
%VENV_PYTHON% scripts/desensitize.py --extend "(?i)某公司名"   # 临时加规则
```

命中会连规则名和上下文一起打出来，逐条确认后按上表替换；`desensitize.py` 自身会被跳过
（它的规则表必然命中自己），`dist/`（打包产物目录）也跳过。二进制默认不扫——PDF 内部数据流会把长串十六进制当真凭证误报。
