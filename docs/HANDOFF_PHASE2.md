# フェーズ2 引継ぎ資料 — 等幅 OTF の生成環境

> 作成: 2026-09-10（フェーズ1 完了時点）。次セッションが **等幅 OTF（フォントファイル）の
> 生成環境** に着手するための資料。仕様の正は [AGENTS.md](../AGENTS.md)、このファイルは
> 「現状」「決まっていること」「決まっていないこと」「手順案」「罠」をまとめたもの。
> 着手前に本資料の §4 の未決事項をユーザーと確定（グリル）してから実装に入ること。

---

## 1. 現状（フェーズ1 の到達点）

| 項目 | 状態 |
| --- | --- |
| 欧文等幅 SVG | `src/glyphs/char_{AGL}_{CP}.svg` 409 字。本家 OTF（v4.0-release）から抽出し、frame を 496u / 992u 枠へ書き換え済み |
| CJK SVG | `src/glyphs/char_uniXXXX_XXXX.svg` 73 字（ひらがな 18・カタカナ 23・半角カタカナ 23・漢字 9）。`fill-rule="evenodd"` |
| デカール PNG | `dist/glyphs_decal{,_square}/{sumi,rust,hazard,patina,nickel,weekday}/` CJK のみ 1,488 点 |
| プレビュー | `docs/previews/hero.png` `glyphset.png`（`build_cjk.py` が自動生成） |
| ビルド | `py -3.14 scripts/build_cjk.py`（約 70 秒）。WARN ゼロで通る |
| 未着手 | **等幅 OTF**、Misskey zip・aiscript 対応表（`glyph_tokens` 方式）、濁点・や行・和文括弧 |

コミット履歴（フェーズ1、すべて未 push）: `cf86b23` scripts → `d104d26` glyphs → `3be84be` docs →
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

## 3. OTF 化の手順案（推奨順）

### 3-A. fontTools で直接組む（推奨）

依存追加は `skia-pathops`（重なり除去・向き正規化）のみ。fontmake / ufo は不要。

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
   （Windows Terminal / WezTerm）で半角 2 個＝全角 1 個に揃うことを目視。
5. 出力先は `dist/fonts/PenchantManufacture-CJK-Mono.otf`（仮）。`build_cjk.py` に
   `font` ステップを足すか、`scripts/build_font.py` を分けるかは §4 で決める。

### 3-B. Fontself（Illustrator 拡張）でユーザーが組む（代替）

本家 OTF は **Fontself Maker 3.6.12**（Illustrator 拡張）製（`meta` テーブルに痕跡）。
CJK 原本の .ai にはアートボード1 に欧文一式もあるので、Fontself 側で advance を
496/992 に固定して書き出す道もある。ただしメトリクス固定の自動化ができず再現性が落ちるため、
3-A を主経路、3-B は検証用・比較用の位置づけを推奨。

---

## 4. 未決事項（着手前にユーザーと確定する）

1. **フォント名**: family / style / PostScript 名（例 `PenchantManufacture-CJK` + `Mono`?）、
   本家 `PenchantManufacture` との衝突回避、`name` テーブルのバージョン文字列と著作権表記。
2. **収録範囲**: 欧文 409 字を全部入れるか（推奨: 入れる。等幅ターミナル用途なら必須）。
   本家の異体字 cmap（同一グリフへの再マップ、現行 0 件）の扱い。
3. **半角カタカナの cmap**: U+FF71〜 のみか、全角カナ U+30A2〜 の半角形として GSUB `hwid` も持たせるか。
4. **East Asian Width Ambiguous 字**（ローマ数字・Ø・± など）を全角にする方針の是非。
   現行の判定はインク幅なので Ⅲ〜ⅻ だけ全角。ターミナルの EAW 設定と衝突しないか確認。
5. **空白グリフ**: `space` = 496u、全角スペース U+3000 = 992u を追加するか（本家は space を持つ）。
6. **`.notdef`／未収録字の扱い**、およびフォールバック用の半角・全角ダミー枠グリフの要否。
7. **出力形式**: OTF(CFF) のみか、TTF も要るか（Windows Terminal は OTF 可）。
8. **ビルド統合**: `build_cjk.py` の 1 ステップにするか、`scripts/build_font.py` に分けるか。
   `dist/fonts/` を追跡するか（`.gitignore` の `dist/` 例外は現状 PNG のみ想定）。
9. **フェーズ1 の残件との順序**: Misskey zip・aiscript 対応表（`glyph_tokens`）を先にやるか後か。
10. **曜日配色の xterm 列**（`docs/WEEKDAY_COLORING_PLAN.md`）をどこで使うか（フォント外の話）。

---

## 5. 罠・環境メモ（フェーズ1 で判明）

- **Windows の実行系**: `py -3.14` を使う（PATH の `python` は依存が入っていない）。
  libcairo が無いので `$env:CAIRO_DLL_DIR="C:\Program Files\KiCad\10.0\bin"` を渡す
  （`build_cjk.py` 冒頭で PATH に足す）。`scipy` は導入済み。
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
