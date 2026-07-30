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

**著作権者**: RadianN_kswg / ラジアン（柏木主税） / **ライセンス**: CC BY 4.0

- **非公開・試験運用**: 公開品質に達するまで GitHub 上は private で運用する。
  ライセンス表記・クレジットの保持義務は公開/非公開に関わらず本家と同一。

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
├── scripts/
│   └── fusion/              ← Fusion 360 用スクリプト（DXF 書き出し等）
└── LICENSE
```

- `.EN-original/` 内のファイルは **変更禁止**（変更は本家リポジトリで行う）。
- 本家のスクリプト・仕様を参照する際は常にサブモジュール側のパスを読む。
- サブモジュール更新は `git submodule update --remote` ＋ 参照コミットの更新コミットで行う。

---

## CJK グリフの制作フロー（試験）

本家はフォント OTF を起点とするが、CJK グリフは未収録のため、
**Fusion 360 ネイティブデータのスケッチ** を起点とする:

```
Fusion 360 (.f3d, 例: Dice (NKO) v1.f3d)
  │
  ├─ [DXF 書き出し] scripts/fusion/export_sketches_dxf.py（Fusion 360 内で実行）
  │         └─ assets/sketches/dxf/char_uniXXXX_XXXX.dxf
  │
  └─ [SVG 化] DXF → アウトラインパス SVG（viewBox 0 0 512 512、本家仕様に準拠）
            └─ src/glyphs/char_uniXXXX_XXXX.svg
```

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

---

## コミットメッセージ規約

本家と同一: `<type>(<scope>): <subject>`（type: `feat` `fix` `build` `docs` `chore` `style`）。
scope に `sketches` `fusion` を追加で用いてよい。
