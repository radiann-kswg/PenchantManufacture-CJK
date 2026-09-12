# AGENTS.md — PenchantManufacture-CJK 共通エージェント指示書

このファイルは **Codex**、**Claude Code**、**GitHub Copilot** が共有する
PenchantManufacture-CJK リポジトリ固有指示の **唯一の正（SSOT）** です。
`CLAUDE.md` は `@AGENTS.md` の参照入口であり、詳細指示を重複記載しません。

---

## プロジェクト概要

**PenchantManufacture フォント収録グリフ／図柄アセットの CJK 対応（かな等）を
試験的に制作する非公開リポジトリ** です。
オリジナルリポジトリ（PenchantManufacture_ImageAssets）はサブモジュール
`.EN-original/` として取得し、設計思想・命名規則・ビルドフロー・技術方針は
**`.EN-original/AGENTS.md` に準拠** します。本ファイルには CJK 固有の差分のみを記載します。

**著作権者**: RadianN_kswg / ラジアン（柏木主税）
**ライセンス**: **CC BY 4.0**（本家と同一。由来を問わず一律。[LICENSE] が正）

- **非公開・試験運用**: 公開品質に達するまで GitHub 上は private で運用する。
  クレジットの保持義務は公開/非公開に関わらず本家と同一。

---

## 頒布・ライセンス方針

**本リポジトリの成果物は、本家由来／CJK 拡張の区別なく一律 CC BY 4.0。**

- **方針変更（2026-09-08）**: 旧版は 2 区分（本家由来 = CC BY 4.0 / CJK 拡張 =
  All Rights Reserved・1 部 500 円以上の有料頒布予定）だったが、等幅・全角版の想定用途が
  **ターミナルアプリ等へのソフトウェア埋め込み**であることを踏まえ、本家と同一の
  CC BY 4.0 に統一した。**有料頒布計画は撤回**。
- 由来の区別が不要になったため、`.EN-original/` 由来物と CJK 新規制作物を
  ライセンス上で切り分ける必要はない。プレビューと実用解像度の出し分けも不要
  （旧「実用解像度は頒布物にのみ同梱」の制約は撤廃）。
- **埋め込みの扱い**: フォントのアプリ・ドキュメント・Web への埋め込みを許諾する。
  CC BY はコピーレフトではないため埋め込み先へライセンスは伝播しない。
  ただし**著作者クレジットとライセンスへのリンクの表記義務は維持**されるので、
  埋め込む側はアプリの「ライセンス」「クレジット」画面等、合理的な方法で表示すること。
- 和文括弧の制作計画は `docs/GLYPH_EXTENSION_PLAN.md`（本家 B8 から移管）を参照。

> **参考（将来の再検討材料）**: フォントをソフトウェアへ埋め込む用途では
> **SIL Open Font License (OFL)** が業界標準で、埋め込み・バンドルの扱いが明文化されている。
> CC BY 4.0 でも埋め込みは可能だが、フォント特有の論点（Reserved Font Name、
> 埋め込み時の帰属表示の方法）は明文化されていない。本家との一貫性を優先して
> CC BY 4.0 を採用しているが、実際にソフトウェア頒布へ組み込む段階で
> **本家とセットでの OFL 移行**を再検討する余地がある（本家だけ／CJK だけの移行は
> 一貫性を壊すので不可）。

---

## 本家からの継承（サブモジュール）

```
PenchantManufacture-CJK/
├── README.md                ← 公開向け概要（プレビュー画像・収録グリフ・ビルド手順）
├── AGENTS.md                ← 本ファイル（CJK 固有差分の SSOT）
├── CLAUDE.md                ← Claude Code 互換入口（@AGENTS.md のみ）
├── .github/
│   └── copilot-instructions.md
├── .EN-original/            ← 【サブモジュール】PenchantManufacture_ImageAssets（読み取り専用）
├── _original-fonts/         ← 原本（読み取り専用、.gitignore 対象）
│   ├── penchant-manufacture_v4.0-release/PenchantManufacture.otf ← 欧文の正
│   └── .develop/
│       └── f-skt penchant-manufactuer-cjk_v4.alpha1.ai   ← CJK グリフの正（アートボード2）
├── src/glyphs/              ← 等幅グリフ SVG（欧文 409 字 ＋ CJK。scripts/build_cjk.py が生成）
├── dist/
│   ├── fonts/PenchantManufactureCJKMono-Regular.otf  ← 等幅 OTF（scripts/build_font.py が生成・検証）
│   ├── glyphs_decal/{sumi,rust,hazard,patina,nickel,weekday}/  ← CJK デカール PNG（幅可変）
│   └── glyphs_decal_square/{同上}/                               ← 同・正方形（Discord）
├── docs/
│   ├── previews/                 ← hero.png / glyphset.png（build_cjk.py が自動生成。dist 更新時に同じコミットへ）
│   ├── HANDOFF_PHASE2.md         ← フェーズ2（等幅 OTF）の記録：確定契約・実装方針・決定事項・罠
│   ├── GLYPH_EXTENSION_PLAN.md   ← 和文括弧・約物の制作計画（本家 B8 から移管）
│   ├── WEEKDAY_COLORING_PLAN.md  ← 曜日漢字の配色（decal `weekday` バリアントの正）
│   └── glyph_aliases.json        ← 本家 extract が生成（自動生成・手編集禁止）
├── scripts/
│   ├── build_cjk.py            ← 一括ビルド（latin → cjk → font → decal → weekday → previews）
│   ├── build_font.py           ← 等幅 OTF の生成と検証（本家 CFF 複製 ＋ CJK SVG → skia-pathops）
│   ├── metrics.py              ← 等幅メトリクス契約の定数と枠判定（SVG 抽出・OTF 生成が共用）
│   ├── extract_ai_glyphs.py    ← .ai → 等幅 SVG（五十音グリッド `GRID` が SSOT）
│   ├── build_previews_cjk.py   ← README 用プレビュー（本家 build_previews を再利用）
│   ├── extract_dice_dxf.py     ← 旧経路: f3d → DXF（代替・温存）
│   └── fusion/                 ← 旧経路: Fusion 360 用スクリプト（代替・温存）
├── assets/                  ← 旧経路の f3d / DXF（代替・温存）
└── LICENSE                  ← CC BY 4.0（本家と同一・一律）
```

- `.EN-original/` 内のファイルは **変更禁止**（変更は本家リポジトリで行う）。
- 本家のスクリプト・仕様を参照する際は常にサブモジュール側のパスを読む。
- サブモジュール更新は `git submodule update --remote` ＋ 参照コミットの更新コミットで行う。

---

## 等幅メトリクス契約（2026-09-10 確定）

本リポジトリの成果物は **等幅（半角／全角）** を契約とする。本家（プロポーショナル）との差分は
横幅の枠だけで、縦は本家契約をそのまま継承する。

| 項目 | 値 | 根拠 |
| --- | --- | --- |
| 単位 | 1mm = 66.1u（capHeight 661u = 欧文 .ai の大文字高 10mm） | 欧文 .ai の設計グリッド |
| 半角枠 | **496u**（7.50mm） | win 帯 991u の半分を切り上げ |
| 全角枠 | **992u**（15.01mm）＝半角×2 厳守 | ターミナルのセル契約 |
| 縦帯 | 本家 OS/2 win 帯 **[−198, 793]** を不変で使用（枠高 991u） | 本家「配置の基準」 |
| かな箱 | 上端 = capHeight 661u（行上端）、下端 = −198u（`y` のディセンダ）＝ 13mm | 作字側の設計 |

- **欧文の半角／全角判定はインク幅**（≤ 496u → 半角）。advance 幅で判定すると
  `m w 4 # &` 等（advance 499〜534u、インク 462u）が全角落ちするため。
  全角行きはローマ数字 `Ⅲ Ⅳ Ⅵ Ⅶ Ⅷ Ⅸ Ⅺ Ⅻ`（大小 16 字）のみ。
- **欧文の枠内配置**: advance が枠に収まれば advance 箱を枠中央、超える字だけインク中央。
- **CJK の枠内配置**: 縦はアートボードの行上端 ↔ 661u に固定、横はインク bbox を枠中央。
  和文括弧（隅寄せ）が要る段階で `extract_ai_glyphs.GRID` にブロック単位のフラグを足す。
- SVG は本家と同じ 512 正方 viewBox・`<!-- frame x=.. y=.. -->` 付き。frame の x が枠幅
  そのものなので、本家 `generate_decal` が無改造で等幅の余白を尊重する。
- CJK の `<path>` は **`fill-rule="evenodd"`**。PyMuPDF が返す矩形（`re`）の向き情報は
  Illustrator 出力では当てにならず（ま・は・ほ と 日 で符号が矛盾）、nonzero だと穴が埋まる。
  抽出時に MuPDF が描いた原本ラスタと照合し、面で残る差があれば WARN を出す
  （`extract_ai_glyphs._verify`）。OTF 化では `build_font.cjk_outline` が skia-pathops で
  nonzero 化（向きの正規化）し、`build_font.verify` が OTF のラスタと SVG のラスタを照合する。
- 枠を超える欧文（現行はなし。`Ⅷ ⅷ` はインク 991u で全角枠に収まる）は WARN 付きで
  書き出し、フォント側で調整して再ビルドする。
- 契約の数値（枠幅・win 帯・capHeight・1mm=66.1u）と欧文の枠判定（`latin_cell`）は
  **`scripts/metrics.py` が唯一の置き場**。SVG 抽出と OTF 生成が同じ値を読む。

### 等幅 OTF（フェーズ2、2026-09-12 完了）

| 項目 | 値 |
| --- | --- |
| ファイル | `dist/fonts/PenchantManufactureCJKMono-Regular.otf`（OpenType/CFF）。git 追跡 |
| 名前 | family `PenchantManufacture CJK Mono` / style `Regular` / PS 名 `PenchantManufactureCJKMono-Regular` / version `0.1.0`（`build_font.VERSION`。字形を足したら上げる） |
| 収録 | 本家 cmap 全部（advance 0 の `.null` `controlLF` `controlCR` は除く）＋ CJK（`src/glyphs/char_uniXXXX_XXXX.svg` 全部）＋ U+3000（992u）。`.notdef` は半角の中空矩形 |
| 欧文 | 本家 CFF の座標を丸めずに複製し、`metrics.latin_cell` の gx だけ平行移動。GPOS kern・GSUB は持ち込まない |
| メトリクス | hhea・typo 660/−400、win 793/198、xAvgCharWidth 496、`post.isFixedPitch=1`、PANOSE proportion=9 |
| EAW | ローマ数字 Ⅲ〜ⅻ は全角のまま。README に ambiguous width = wide 前提と明記。他の Ambiguous 字は半角 |
| 再現性 | `head.created/modified` を固定（`build_font.BUILD_TIME`）。字形を変えなければ再ビルドはバイト一致 → PNG と同じく字形変更時のみコミット |
| 検証 | `build_font.verify`: advance ∈ {496, 992}／cmap の過不足／欧文を本家 `extract_glyphs` で再抽出して `src/glyphs` と座標一致／CJK は winding ラスタで SVG と一致／「にほん」「ｺﾝﾃﾅ」の幅合計。NG があれば非 0 終了 |
| 未採用 | GSUB `hwid`（半角カナは cmap のみ）、TTF の常時出力（`--ttf` で任意生成）、mac 名前レコード（name は Windows platform のみ） |

---

## CJK グリフの制作フロー

CJK グリフの正は **Illustrator 原本 `_original-fonts/.develop/f-skt penchant-manufactuer-cjk_v4.alpha1.ai`
のアートボード2**。.ai は PDF 互換なので PyMuPDF で直接読む（Illustrator・Adobe コネクタ不要。
Adobe コネクタは手動プレビュー用途に限り、ビルドには使わない）。

```
py -3.14 scripts/build_cjk.py        # macOS: venv の python（例: ../.venv/bin/python scripts/build_cjk.py）
  1. latin   本家 extract_glyphs.extract_all（OTF）→ transform/frame を等幅枠へ書き換え
  2. cjk     extract_ai_glyphs.extract_all（.ai アートボード2）→ src/glyphs/char_uniXXXX_XXXX.svg
  3. font    build_font.build（本家 CFF 複製 ＋ CJK SVG → skia-pathops）→ dist/fonts/*.otf → verify
  4. decal   本家 generate_decal.render を CJK グリフだけに適用（5 スキーム、幅可変＋正方形）
  5. weekday 日〜土 7 字を曜日配色（docs/WEEKDAY_COLORING_PLAN.md、build_cjk.WEEKDAY）で描画
  6. previews docs/previews/hero.png, glyphset.png（README 冒頭のサムネイル）
```

- `--no-decal` は SVG と OTF まで、`--no-font` は OTF を飛ばす。OTF だけなら
  `py -3.14 scripts/build_font.py`（libcairo 不要、約 5 秒）。

- **実行環境**: Python 3.11+。Windows では `py -3.14`（PATH の `python` は依存が入っていない）。
  依存は `py -3.14 -m pip install -r requirements.txt`（本家の requirements を `-r` で取り込み＋ PyMuPDF）。
  本家 decal が使う **libcairo の DLL は pip では入らない**ので、手元の DLL ディレクトリを
  環境変数で渡す: `$env:CAIRO_DLL_DIR = "C:\Program Files\KiCad\10.0\bin"`（KiCad 同梱の
  `cairo-2.dll` を流用。GTK ランタイム等でも可）。
- **実行環境（macOS）**: Python 3.14 の venv（例: ImageAssets 直下の共有 `../.venv`）へ
  `pip install -r requirements.txt`。libcairo は `brew install cairo` で入れる。Homebrew の
  `/opt/homebrew/lib` は dyld の既定の探索先に無いため `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`
  を渡す（共有 venv では `site-packages/sitecustomize.py` が起動時に自動設定）。
  コマンド例の `py -3.14` は venv の `python` に読み替える。
- 本家スクリプトは `sys.path` 経由で import する。**`.EN-original/` は変更しない**。
  本家 `generate_decal` の出力先はモジュール定数固定なので、`build_cjk.decal` が
  render / `_save_all_sizes` / `frame_box` を直接呼んで CJK 側の `dist/` へ書く。
- 描画一致統合（`dedupe_renders`）は CJK では行わない（同形グリフが無い）。
- 欧文の decal PNG は本家にあるため CJK 側では生成しない（SVG のみ等幅版を持つ）。
- トークン定義・aiscript・Misskey zip は未着手（Misskey 登録段階で本家 `glyph_tokens` 方式に倣う）。
- フェーズ2（等幅 OTF）は 2026-09-12 に完了。決定事項と罠は `docs/HANDOFF_PHASE2.md`。
  次はフェーズ3（Misskey zip・aiscript 対応表、収録字の拡充）。

### アートボードの配置規則（`extract_ai_glyphs.GRID` が SSOT）

| ブロック | 原点(mm, 左上のインク左端) | ピッチ | 枠 | 行文字列 |
| --- | --- | --- | --- | --- |
| ひらがな | (5.35, 37.04) | 15×15 | 992u | `あいうえおかきくけこさしすせそ` / `たちつてとなにぬねのはひふへほ` / `まみむめもらりるれろわをん` |
| カタカナ | (5.35, 97.04) | 15×15 | 992u | 同上のカタカナ |
| 半角カタカナ | (244.34, 97.04) | **10**×15 | 496u | 同上（U+FF71〜） |
| 漢字 | (5.35, 177.04) | 15×15 | 992u | `日月火水木金土` / `全年` |

- 各パスは左上座標から `floor((座標 − 原点 + 1.5mm) / ピッチ)` でセルへ割り当てる
  （手置きのズレ ±1mm を吸収、インク幅 ≤ 12mm が前提）。行文字列のインデックスが列。
- 字を足すときは **行文字列を伸ばすか行を追加**する。や行・小書き・濁点は追加時にブロック調整。
- 行文字列に無い列にパスがあると WARN、グリッド外のパスは無視して件数を報告する。
- 旧経路（Fusion `.f3d` → `extract_dice_dxf.py` → DXF）は代替として温存し、ビルドには乗せない。

### 命名規則（本家準拠＋CJK 拡張）

かな・カタカナ・漢字は AGL 名を持たないため、本家のフォールバック規則 `uniXXXX` を用いる
（`extract_ai_glyphs.py` が生成。欧文は本家と同じ AGL 名ステム）:

| 文字 | コードポイント | ステム |
| --- | --- | --- |
| う | U+3046 | `char_uni3046_3046` |
| お | U+304A | `char_uni304A_304A` |
| こ | U+3053 | `char_uni3053_3053` |
| ち | U+3061 | `char_uni3061_3061` |
| ま | U+307E | `char_uni307E_307E` |
| ん | U+3093 | `char_uni3093_3093` |
| ｱ | U+FF71 | `char_uniFF71_FF71` |
| 日 | U+65E5 | `char_uni65E5_65E5` |

---

## 絶対に行わないこと

- `.EN-original/`（サブモジュール）内ファイルの変更・削除
- `_original-fonts/` 内ファイルの変更・削除
- `src/glyphs/` `dist/` への直接ファイル配置（`scripts/build_cjk.py` / `build_font.py` 経由のみ）
- 等幅枠（496u / 992u）・win 帯・`GRID` の原点／ピッチを断りなく変えること（登録済み絵文字の再アップロードを招く）
- フォント名（family / PS 名）・`unitsPerEm`・縦メトリクスを断りなく変えること（インストール済みフォントの差し替えを招く）
- 第三者フォント・商用グリフのグリフパス流用
- ライセンス表記（CC BY 4.0 / 著作者名）の削除・改ざん
- 本家（CC BY 4.0）と異なるライセンスを CJK 拡張部分へ付与すること
  （2026-09-08 に一律 CC BY 4.0 へ統一済み。区分を再導入しない）

---

## コミットメッセージ規約

本家と同一: `<type>(<scope>): <subject>`（type: `feat` `fix` `build` `docs` `chore` `style`）。
scope に `sketches` `fusion` を追加で用いてよい。
