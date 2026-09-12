# フェーズ2 記録 — 等幅 OTF の生成環境

> 作成: 2026-09-10（フェーズ1 完了時点）。**2026-09-12 にフェーズ2 完了**（`scripts/build_font.py`、
> `dist/fonts/PenchantManufactureCJKMono-Regular.otf` v0.1.0）。仕様の正は [AGENTS.md](../AGENTS.md)、
> このファイルは「確定契約」「実装方針」「§4 の決定事項」「罠」の記録。§0 に完了時点の要約を置く。

---

## 0. 完了時点の要約（2026-09-12、Windows で実装）

| 項目 | 結果 |
| --- | --- |
| 実装 | `scripts/build_font.py`（生成 `build` ＋ 検証 `verify`）、`scripts/metrics.py`（契約定数の唯一の置き場。`extract_ai_glyphs` / `build_cjk` も参照するよう変更） |
| 出力 | `dist/fonts/PenchantManufactureCJKMono-Regular.otf`（487 グリフ / cmap 486 / 約 75 KB）。`--ttf` で TTF（約 42 KB）も生成可 |
| 統合 | `build_cjk.py` のステップ 3/6（`--no-font` で省略）。単独実行は約 5 秒、libcairo 不要 |
| 検証 | advance ∈ {496, 992}・cmap・欧文の座標一致・CJK ラスタ一致・幅合計 すべて OK。2 回ビルドして SHA-256 一致（再現性）。SVG / PNG は変更前とバイト一致（metrics.py 化で生成物は変わらない） |
| 目視 | Pillow で描画し、半角 2 字＝全角 1 字・は ほ ま 日 ロ の穴・半角カナを確認（ターミナル実機は未確認） |
| 依存 | `skia-pathops`（requirements.txt に追加。cp310-abi3 wheel で Python 3.14 でも導入可） |

---

## 1. 現状（フェーズ1 の到達点）

| 項目 | 状態 |
| --- | --- |
| 欧文等幅 SVG | `src/glyphs/char_{AGL}_{CP}.svg` 409 字。本家 OTF（v4.0-release）から抽出し、frame を 496u / 992u 枠へ書き換え済み |
| CJK SVG | `src/glyphs/char_uniXXXX_XXXX.svg` 73 字（ひらがな 18・カタカナ 23・半角カタカナ 23・漢字 9）。`fill-rule="evenodd"` |
| デカール PNG | `dist/glyphs_decal{,_square}/{sumi,rust,hazard,patina,nickel,weekday}/` CJK のみ 1,488 点 |
| プレビュー | `docs/previews/hero.png` `glyphset.png`（`build_cjk.py` が自動生成） |
| ビルド | Windows: `py -3.14 scripts/build_cjk.py`（約 70 秒）／macOS: venv の `python scripts/build_cjk.py`（約 30 秒）。WARN ゼロで通る |
| 未着手 | ~~等幅 OTF~~（2026-09-12 完了）、Misskey zip・aiscript 対応表（`glyph_tokens` 方式）、濁点・や行・和文括弧 |

コミット履歴（フェーズ1、push 済み）: `cf86b23` scripts → `d104d26` glyphs → `3be84be` docs →
`c60e743`/`cd619b0` v4.alpha1 切替 → `e61d18e`/`60a8630` 穴修正 → 本資料・README のコミット。

---

## 2. 確定している契約（OTF に持ち込む値）

| 項目 | 値 | 備考 |
| --- | --- | --- |
| unitsPerEm | 1000 | 本家と同じ |
| 半角 advance | **496u** | 7.50mm。`m w 4 # &` 等（本家 advance 499〜534u）も半角 |
| 全角 advance | **992u** | 半角×2 厳守。ローマ数字 Ⅲ Ⅳ Ⅵ Ⅶ Ⅷ Ⅸ Ⅺ Ⅻ ＋ 小文字 16 字、かな・カタカナ・漢字 |
| 半角/全角の判定 | インク幅 ≤ 496u → 半角 | advance ではない（`build_cjk.monospace_latin`） |
| 欧文の枠内位置 | advance 箱を枠中央、advance > 枠 ならインク中央 | `gx = (cell-adv)/2` or `(cell-ink_w)/2 - ink_x0` |
| CJK の枠内位置 | 横: インク bbox 中央／縦: 行上端 = capHeight 661u | 12mm かな → 下端 −131u、13mm 漢字 → 下端 −198u |
| 縦メトリクス | hhea/typo 660 / −400 / 0、**win 793 / 198**（本家不変） | 変更禁止（本家の絵文字クロップ契約） |
| 単位換算 | 1mm = 66.1u（`extract_ai_glyphs.UNITS_PER_MM`） | 欧文原本の大文字高 10mm = 661u |
| ライセンス | CC BY 4.0（由来を問わず一律） | OFL 移行は本家とセットでのみ再検討（AGENTS.md） |

SVG 側の等幅情報は各ファイルの `<!-- frame x=X0,X1 y=0,Y1 -->` にあり、
`(X1−X0) / 0.512` が advance（496 or 992）、`X0` が枠左端の px 位置。
SVG px → フォント座標は `u_x = (px_x − X0) / 0.512`、`u_y = 793 − px_y / 0.512`。

---

## 3. OTF 化の手順（3-A で実装済み）

### 3-A. fontTools で直接組む（採用・実装済み）

依存追加は `skia-pathops`（重なり除去・向き正規化）のみ。fontmake / ufo は不要。
実装との差分: 欧文は T2CharString を「再構築」ではなく本家 glyphSet を `TransformPen` →
`T2CharStringPen(roundTolerance=0)` で描き直す（座標は丸めず本家のまま）。CJK は
`T2CharStringPen` の既定（整数へ丸め）。検証 4 の `hb-shape` は使わず、fontTools の `hmtx` 合計と
winding ラスタ（numpy）で代替した。

1. **欧文**: 本家 OTF から CFF CharString をそのまま複製し、`hmtx` の advance を 496/992 に、
   アウトラインを `gx` だけ平行移動（T2 CharString の再構築は `T2CharStringPen` に
   `TransformPen` を噛ませる）。SVG を経由しないので字形の劣化がない。
2. **CJK**: `src/glyphs/char_uni*.svg` の `<path d>` を `fontTools.svgLib.path.SVGPath` で
   読み、`TransformPen`（px → u、y 反転、枠左端 X0 を原点へ）→ skia-pathops で
   **evenodd → nonzero 化＋重なり除去**（`pathops.Path.simplify(fix_winding=True)`、
   入力の fillType は EVEN_ODD）→ `T2CharStringPen`。
   直線のみ（ベジェ 0 本）なので CFF の hint 無しで問題ない。
3. **テーブル**: `fontTools.fontBuilder.FontBuilder(1000, isTTF=False)` で
   `setupGlyphOrder / setupCharacterMap / setupCFF / setupHorizontalMetrics /
   setupHorizontalHeader(660, −400) / setupOS2(win 793/198, typo 660/−400, xAvgCharWidth=496,
   panose proportion=9 monospaced) / setupNameTable / setupPost(isFixedPitch=1)`。
   `GPOS kern` は等幅なので**持ち込まない**（本家の Ⅹ 直後字詰めも不要）。GSUB は本家に無い。
4. **検証**（最小の自己チェック）: 全グリフの advance ∈ {496, 992}、CJK の cmap が
   `GRID` の文字集合と一致、`hb-shape` 相当（`fontTools` の `getGlyphSet` でも可）で
   「にほん」「ｺﾝﾃﾅ」の合計幅が 992×3 / 496×4 になること、任意ターミナル
   （Windows Terminal / WezTerm / macOS のターミナル・iTerm2）で半角 2 個＝全角 1 個に揃うことを目視。
5. 出力先は `dist/fonts/PenchantManufacture-CJK-Mono.otf`（仮）。`build_cjk.py` に
   `font` ステップを足すか、`scripts/build_font.py` を分けるかは §4 で決める。

### 3-B. Fontself（Illustrator 拡張）でユーザーが組む（代替）

本家 OTF は **Fontself Maker 3.6.12**（Illustrator 拡張）製（`meta` テーブルに痕跡）。
CJK 原本の .ai にはアートボード1 に欧文一式もあるので、Fontself 側で advance を
496/992 に固定して書き出す道もある。ただしメトリクス固定の自動化ができず再現性が落ちるため、
3-A を主経路、3-B は検証用・比較用の位置づけを推奨。

---

## 4. 決定事項（2026-09-12 にユーザーと確定。旧「未決事項」）

| # | 項目 | 決定 |
| --- | --- | --- |
| 1 | フォント名 | family `PenchantManufacture CJK Mono` / style `Regular` / PS 名 `PenchantManufactureCJKMono-Regular`。version `0.1.0`（.ai v4.alpha1 対応、`build_font.VERSION`）。著作権 `© RadianN_kswg / ラジアン（柏木主税）`（name ID 0。CFF Notice は latin-1 限定なので `© RadianN_kswg`）、license ID 13/14 に CC BY 4.0 と URL |
| 2 | 収録範囲 | 欧文 409 字を全部（本家 cmap をそのまま継承。異体字 cmap は 0 件のまま継承されるので特別扱い不要） |
| 3 | 半角カナ cmap | U+FF71〜 の cmap のみ。GSUB `hwid` は入れない（ターミナルは feature を適用しない） |
| 4 | EAW Ambiguous | ローマ数字 Ⅲ〜ⅻ は 992u のまま（インク 991u で縮められない）。README に ambiguous width = wide 前提と明記。± Ø 等は半角のまま（混在許容） |
| 5 | 空白 | `space` 496u（本家 219u から変更）、U+3000 `uni3000` 992u を追加。U+00A0 は本家の `nonbreakingspace`（空・496u）を継承 |
| 6 | .notdef | 496u の中空矩形 1 つ。全角ダミー枠は作らない。本家の advance 0 の `.null` `controlLF` `controlCR` は持ち込まない（全 advance を {496, 992} に揃える） |
| 7 | 出力形式 | OTF(CFF) のみ。`--ttf` で TTF も生成可（直線のみなので `TTGlyphPen` ＋ `ReverseContourPen` で無劣化） |
| 8 | ビルド統合 | `scripts/build_font.py` を分け、`build_cjk.py` のステップ 3/6 から呼ぶ（当初案の 6/6 から前倒し。`--no-decal` でも OTF は作る）。`dist/fonts/*.otf` は git 追跡し、`head` の日時固定で再現性を確保、字形変更時のみコミット |
| 9 | 順序 | OTF を先（本資料）。Misskey zip・aiscript 対応表はフェーズ3 |
| 10 | 曜日配色 xterm 列 | フォント外＝対象外 |

### 残件・次の候補

- **ターミナル実機での目視**（Windows Terminal / WezTerm / iTerm2）: 半角 2 個＝全角 1 個、
  ambiguous=wide でのローマ数字、行間（win 帯 991u vs typo 1060u の扱い）。
- 字形追加時: `.ai` 更新 → `build_cjk.py` → `build_font.VERSION` を上げる → OTF をコミット。
- 将来 GSUB `hwid` / `vert`、OFL 移行（本家とセット）は AGENTS.md の方針どおり再検討。

---

## 5. 罠・環境メモ

### フェーズ2 で判明

- **`char_uni*` の glob は欧文も拾う**: `char_union_222A` `char_uni2071_2071`（AGL 名が無く
  `uniXXXX` フォールバックの字も本家に 6 字ある）。CJK の判定は `build_font.cjk_codepoint`
  （`^char_uni([0-9A-F]{4})_\1$`）で行い、`stem[8:12]` の切り出しや `startswith("char_uni")` は使わない。
  同様に本家グリフ名にも `uniXXXX` があるので、「丸めるかどうか」は名前ではなく `Glyph.exact` で持つ。
- **CFF の文字列は latin-1 限定**: 日本語を含む著作権表記は `name` テーブルにだけ置く
  （`fb.setupCFF` の `Notice` に入れると `UnicodeEncodeError`）。`name` は Windows platform のみ
  （`mac=False`。mac roman では日本語が入らない）。
- **再現性**: `FontBuilder` は `head.created/modified` に現在時刻を入れる。`setupHead` に固定値
  （`BUILD_TIME`）を渡す。`TTFont(recalcTimestamp=False)` は FontBuilder が既定でやってくれる。
- **検証の一時ファイル**: `tempfile.TemporaryDirectory` を抜けると消えるので、再抽出 SVG は
  `with` の中で読み切る。
- **T2CharStringPen の丸め**: 既定 `roundTolerance=0.5` は全座標を整数化する。本家複製は
  `roundTolerance=0`（実数のまま。OTF が 75 KB になるのはこのため。TTF は整数なので 42 KB）。
- **PowerShell の文字化け**: Desktop Commander 経由では `[Console]::OutputEncoding` を UTF-8 に、
  `$env:PYTHONUTF8=1` を付けると Python の日本語出力が読める。`Get-Content` は `-Encoding UTF8`。

### フェーズ1 で判明

- **Windows の実行系**: `py -3.14` を使う（PATH の `python` は依存が入っていない）。
  libcairo が無いので `$env:CAIRO_DLL_DIR="C:\Program Files\KiCad\10.0\bin"` を渡す
  （`build_cjk.py` 冒頭で PATH に足す）。`scipy` は導入済み。
- **macOS の実行系**（2026-09-11 に Windows から引き継ぎ）: Python 3.14 の venv（ImageAssets 直下の共有 `.venv`）。
  libcairo は `brew install cairo`。Homebrew の `/opt/homebrew/lib` は dyld の既定の探索先に無いので
  `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` を渡す（共有 venv では `sitecustomize.py` が自動設定）。
  原本 `_original-fonts/` は Dropbox の `Creative Cloud Files/Illustrator/作字/` から複製した
  （`_export/penchant-manufacture_v4.0-release/` 一式と、`f-skt penchant-manufactuer-cjk.ai` を
  `.develop/f-skt penchant-manufactuer-cjk_v4.alpha1.ai` として）。この構成で全ステップを再ビルドし、
  SVG 482 字・デカール PNG 1,488 点がコミット済みの成果物とバイト一致（差分は `docs/glyph_aliases.json`
  の生成時刻のみ）することを確認済み。
- **PyMuPDF の `re` 向き**は当てにならない（`ま は ほ` と `日 ロ` で ±1 の意味が矛盾）。
  SVG は evenodd で逃げているので、**OTF 化では skia-pathops で必ず向きを正規化**する。
  `extract_ai_glyphs._verify` が MuPDF ラスタと照合しているので、抽出側の崩れは WARN で出る。
- **本家スクリプトの再利用**: `.EN-original/scripts` を `sys.path` に足して import。
  `generate_decal` は出力先がモジュール定数固定なので `render / _save_all_sizes / frame_box`
  を直接呼ぶ（`build_cjk.decal`）。`extract_glyphs.extract_all(prune=True)` は CJK SVG を
  消すので `prune=False` ＋ 自前 prune。
- **Illustrator 原本の更新手順**: 新しい .ai を `_original-fonts/.develop/` に置き、
  `extract_ai_glyphs.AI_PATH` と AGENTS.md のパスを更新 → `GRID` に行文字列を足す →
  `--dry-run` で「行文字列の割り当てがありません」「グリッド外」の WARN が無いことを確認 →
  フルビルド。原本は `.gitignore` 対象なので生成物（`src/` `dist/` `docs/previews/`）を
  コミットに含める。
- **本家 OTF の更新**: `build_cjk.FONT`（現行 `_original-fonts/penchant-manufacture_v4.0-release/`）。
  advance 変更は等幅判定に影響しうる（インク幅 > 496u になった字が全角へ落ちる）。
- **コミット規約**: `<type>(<scope>): <subject>`。生成物は `build(glyphs)`、スクリプトは
  `feat/fix(scripts)`、文書は `docs` で分ける。日本語メッセージは `-F` でファイルから渡す。
- Adobe コネクタ（`document_render_vector` 等）はビルドに使わない。.ai は PDF 互換で
  PyMuPDF が直接読める（直線パスのみ）。
