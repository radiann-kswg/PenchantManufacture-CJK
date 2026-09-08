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
├── AGENTS.md                ← 本ファイル（CJK 固有差分の SSOT）
├── CLAUDE.md                ← Claude Code 互換入口（@AGENTS.md のみ）
├── .github/
│   └── copilot-instructions.md
├── .EN-original/            ← 【サブモジュール】PenchantManufacture_ImageAssets（読み取り専用）
├── _original-fonts/         ← 原本（読み取り専用、.gitignore 対象）
│   ├── f-skt penchant-manufactuer.ai
│   └── penchant-manufacture_v3.1-release/
├── assets/
│   └── sketches/dxf/        ← Fusion 360 スケッチの DXF 書き出し（CJK グリフソース）
├── src/glyphs/              ← CJK グリフ SVG（DXF → SVG 変換後、本家命名規則に従う）
├── docs/
│   └── GLYPH_EXTENSION_PLAN.md ← 和文括弧・約物の制作計画（本家 B8 から移管）
├── scripts/
│   └── fusion/              ← Fusion 360 用スクリプト（DXF 書き出し等）
└── LICENSE                  ← CC BY 4.0（本家と同一・一律）
```

- `.EN-original/` 内のファイルは **変更禁止**（変更は本家リポジトリで行う）。
- 本家のスクリプト・仕様を参照する際は常にサブモジュール側のパスを読む。
- サブモジュール更新は `git submodule update --remote` ＋ 参照コミットの更新コミットで行う。

---

## CJK グリフの制作フロー（試験）

本家はフォント OTF を起点とするが、CJK グリフは未収録のため、
**Fusion 360 ネイティブデータのスケッチ** を起点とする:

```
Fusion 360 (.f3d, 例: assets/fusion/Dice (NKO) v1.f3d)
  │
  ├─ [DXF 書き出し] scripts/extract_dice_dxf.py（Fusion 不要・f3d 内 ASM バイナリを直接パース）
  │         ├─ assets/sketches/dxf/char_uniXXXX_XXXX.dxf（6字、mm単位、閉LWPOLYLINE）
  │         └─ assets/sketches/dxf/preview.png（検証用）
  │
  └─ [SVG 化] DXF → アウトラインパス SVG（viewBox 0 0 512 512、本家仕様に準拠）
            └─ src/glyphs/char_uniXXXX_XXXX.svg
```

- `scripts/fusion/`（Fusion 360 内で実行する DXF 書き出しスクリプト）は
  Fusion が使える環境向けの代替経路として温存する。
- サイコロ6面のグリフは「う お こ ち ま ん」。面ID・鏡像・回転の同定は
  `scripts/extract_dice_dxf.py` の `FACE_MAP` が SSOT（彫り込み底面の重複
  ループ＝1109「お」・922「ま」は除外済み）。

### 命名規則（本家準拠＋CJK 拡張）

かなは AGL 名を持たないため、本家のフォールバック規則 `uniXXXX` を用いる:

| 文字 | コードポイント | ステム |
| --- | --- | --- |
| う | U+3046 | `char_uni3046_3046` |
| お | U+304A | `char_uni304A_304A` |
| こ | U+3053 | `char_uni3053_3053` |
| ち | U+3061 | `char_uni3061_3061` |
| ま | U+307E | `char_uni307E_307E` |
| ん | U+3093 | `char_uni3093_3093` |

---

## 絶対に行わないこと

- `.EN-original/`（サブモジュール）内ファイルの変更・削除
- `_original-fonts/` 内ファイルの変更・削除
- 第三者フォント・商用グリフのグリフパス流用
- ライセンス表記（CC BY 4.0 / 著作者名）の削除・改ざん
- 本家（CC BY 4.0）と異なるライセンスを CJK 拡張部分へ付与すること
  （2026-09-08 に一律 CC BY 4.0 へ統一済み。区分を再導入しない）

---

## コミットメッセージ規約

本家と同一: `<type>(<scope>): <subject>`（type: `feat` `fix` `build` `docs` `chore` `style`）。
scope に `sketches` `fusion` を追加で用いてよい。
