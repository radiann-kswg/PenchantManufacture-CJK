"""等幅メトリクス契約（AGENTS.md「等幅メトリクス契約」が正）の唯一の置き場。

SVG 抽出（``extract_ai_glyphs`` / ``build_cjk``）と OTF 生成（``build_font``）が同じ値を使う。
``build_font`` は libcairo に依存しないので、cairosvg を import する ``extract_ai_glyphs``
からではなく本モジュールから読む。
"""
from __future__ import annotations

UPM = 1000
VIEWBOX = 512                     # 本家 extract_glyphs と同じ SVG キャンバス（px）
SCALE = VIEWBOX / UPM             # フォント座標(u) → SVG px
WIN_TOP, WIN_BOTTOM = 793, -198   # 本家 OS/2 win 帯（不変）。win 帯上端が SVG の y=0
TYPO_ASCENDER, TYPO_DESCENDER = 660, -400   # 本家 hhea / typo（不変）
CAP_HEIGHT = 661                  # 行上端が来るフォント座標（大文字上端）
X_HEIGHT = 462                    # 本家 OS/2 sxHeight
UNITS_PER_MM = CAP_HEIGHT / 10.0  # 欧文 .ai の大文字高 10mm = 661u
CELL_HALF, CELL_FULL = 496, 992   # 半角 / 全角 枠幅（u）


def latin_cell(advance: float, ink_x0: float, ink_x1: float) -> tuple[int, float]:
    """本家（プロポーショナル）グリフの (枠幅, 枠内オフセット gx) を返す。

    判定はインク幅（≤ 496u → 半角）。advance で判定すると ``m w 4 # &`` 等
    （advance 499〜534u、インク 462u）が全角へ落ちる。
    配置は advance が枠に収まれば advance 箱を枠中央、超える字だけインク中央。
    """
    ink_w = ink_x1 - ink_x0
    cell = CELL_HALF if ink_w <= CELL_HALF else CELL_FULL
    gx = (cell - advance) / 2 if advance <= cell else (cell - ink_w) / 2 - ink_x0
    return cell, gx


def cell_left_px(cell: int) -> float:
    """枠をキャンバス中央へ置いたときの枠左端（SVG px）。``<!-- frame x=.. -->`` の X0。"""
    return (VIEWBOX - cell * SCALE) / 2
