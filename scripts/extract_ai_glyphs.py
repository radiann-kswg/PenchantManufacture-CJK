"""Illustrator 原本（.ai）の CJK アートボードから等幅グリフ SVG を抽出する。

.ai は PDF 互換なので PyMuPDF で直接読む（Adobe コネクタ・Illustrator 不要）。
アートボード上の配置は ``GRID`` の五十音グリッド（mm 単位）が SSOT で、
各パスは左上座標からセル（行・列）へ割り当て、行文字列で文字を同定する。

出力は本家 ``extract_glyphs.py`` と同じ 512 正方 SVG（``<!-- frame -->`` 付き）:
    縦: 行上端 ↔ capHeight 661u。win 帯 [-198, 793] 上端が y=0（本家契約そのまま）
    横: インク bbox を枠（半角 496u / 全角 992u）の中央に置く
    塗り: fill-rule=evenodd（PDF 側の周り方に依存せず穴を再現。MuPDF のラスタと照合して検証）
    ファイル名: char_uniXXXX_XXXX.svg（かな・漢字は AGL 名を持たないため）

使い方:
    python scripts/extract_ai_glyphs.py            # src/glyphs/ へ書き出し
    python scripts/extract_ai_glyphs.py --dry-run
    python scripts/extract_ai_glyphs.py --ai "path/to/other.ai"
"""
from __future__ import annotations

import math
from collections import defaultdict
from io import BytesIO
from pathlib import Path

import cairosvg
import click
import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion
try:
    import pymupdf
except ImportError:  # 古い配布名
    import fitz as pymupdf

ROOT = Path(__file__).resolve().parent.parent
AI_PATH = ROOT / "_original-fonts" / ".develop" / "f-skt penchant-manufactuer-cjk_v4.alpha1.ai"
OUT_DIR = ROOT / "src" / "glyphs"
ARTBOARD = 1                # 0 始まり。アートボード2 = CJK

# ── メトリクス契約（AGENTS.md「等幅メトリクス」が正） ──
UPM = 1000
VIEWBOX = 512
WIN_TOP, WIN_BOTTOM = 793, -198   # 本家 OS/2 win 帯（不変）
CAP_HEIGHT = 661                  # 行上端が来るフォント座標（大文字上端）
UNITS_PER_MM = CAP_HEIGHT / 10.0  # 欧文 .ai の大文字高 10mm = 661u
CELL_HALF, CELL_FULL = 496, 992   # 半角 / 全角 枠幅（u）

PT_TO_MM = 25.4 / 72
SLACK_MM = 1.5   # 格子線を左上へずらす量。手置きのズレ（い は -0.5mm、月 は -0.5mm）を吸収しつつ、
                 # 右側・下側の断片（インク幅 ≤ 12mm）が隣セルへ落ちない範囲

# ── 五十音グリッド SSOT（原点 = 左上のインク左端 mm、ピッチ mm、枠幅 u、行文字列） ──
# 列 = 行文字列のインデックス。字を足すときは行文字列を伸ばすか行を追加する。
GRID: tuple[tuple[str, float, float, float, float, int, tuple[str, ...]], ...] = (
    ("hiragana", 5.35, 37.04, 15.0, 15.0, CELL_FULL, (
        "あいうえおかきくけこさしすせそ",
        "たちつてとなにぬねのはひふへほ",
        "まみむめもらりるれろわをん",
    )),
    ("katakana", 5.35, 97.04, 15.0, 15.0, CELL_FULL, (
        "アイウエオカキクケコサシスセソ",
        "タチツテトナニヌネノハヒフヘホ",
        "マミムメモラリルレロワヲン",
    )),
    ("halfwidth-katakana", 244.34, 97.04, 10.0, 15.0, CELL_HALF, (
        "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿ",
        "ﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎ",
        "ﾏﾐﾑﾒﾓﾗﾘﾙﾚﾛﾜｦﾝ",
    )),
    ("kanji", 5.35, 177.04, 15.0, 15.0, CELL_FULL, (
        "日月火水木金土",
        "全年",
    )),
)


def _path_d(items: list, close: bool) -> str:
    """PyMuPDF の描画アイテム列を mm 単位の SVG パス文字列にする。"""
    out: list[str] = []
    cur = None
    for it in items:
        op = it[0]
        if op == "re":
            # PyMuPDF の re は向き情報（±1）が Illustrator 出力では当てにならない
            # （ま・は・ほ と 日 で符号が矛盾する）。穴は fill-rule=evenodd で表すので
            # 矩形の周り方は問わない。
            r = it[1]
            x0, y0, x1, y1 = (v * PT_TO_MM for v in (r.x0, r.y0, r.x1, r.y1))
            out.append(f"M{x0:.3f} {y0:.3f}H{x1:.3f}V{y1:.3f}H{x0:.3f}Z")
            cur = None
            continue
        p0 = it[1]
        if cur is None or (p0.x, p0.y) != cur:
            out.append(f"M{p0.x * PT_TO_MM:.3f} {p0.y * PT_TO_MM:.3f}")
        if op == "l":
            p1 = it[2]
            out.append(f"L{p1.x * PT_TO_MM:.3f} {p1.y * PT_TO_MM:.3f}")
        elif op == "c":
            p1, p2, p3 = it[2], it[3], it[4]
            out.append(f"C{p1.x * PT_TO_MM:.3f} {p1.y * PT_TO_MM:.3f} "
                       f"{p2.x * PT_TO_MM:.3f} {p2.y * PT_TO_MM:.3f} "
                       f"{p3.x * PT_TO_MM:.3f} {p3.y * PT_TO_MM:.3f}")
            p1 = p3
        else:
            raise SystemExit(f"未対応の描画オペレータ: {op}")
        cur = (p1.x, p1.y)
    if close and out:
        out.append("Z")
    return "".join(out)


def _locate(x_mm: float, y_mm: float) -> tuple[int, str, int, int] | None:
    """左上座標（mm）から (GRID インデックス, 文字, 行, 列) を返す。格子外なら None。"""
    for gi, (_name, x0, y0, px, py, _cell, rows) in enumerate(GRID):
        col = math.floor((x_mm - x0 + SLACK_MM) / px + 1e-9)
        row = math.floor((y_mm - y0 + SLACK_MM) / py + 1e-9)
        if row < 0 or col < 0 or row >= len(rows):
            continue
        if x_mm - x0 + SLACK_MM >= px * max(len(r) for r in rows):
            continue
        if col >= len(rows[row]):
            return gi, "", row, col
        return gi, rows[row][col], row, col
    return None


def glyph_svg(char: str, paths: list[str], ink: tuple[float, float, float, float],
              row_top_mm: float, cell: int) -> str:
    """1 文字分のパス群（mm 座標）を等幅フレーム付き 512 SVG にする。"""
    ink_x0, _ink_y0, ink_x1, _ink_y1 = ink
    ink_w_u = (ink_x1 - ink_x0) * UNITS_PER_MM
    if ink_w_u > cell + 0.5:
        print(f"  WARN: {char} のインク幅 {ink_w_u:.0f}u が枠 {cell}u を超えています")

    scale = VIEWBOX / UPM
    tx_cell = (VIEWBOX - cell * scale) / 2           # 枠をキャンバス中央へ
    # mm → フォント座標(u): x は枠内中央寄せ、y は行上端 ↔ CAP_HEIGHT
    #   u_x = (x_mm - ink_x0) * k + (cell - ink_w_u) / 2
    #   u_y = CAP_HEIGHT - (y_mm - row_top_mm) * k
    # これを SVG px へ: px_x = u_x * scale + tx_cell, px_y = (WIN_TOP - u_y) * scale
    k = UNITS_PER_MM
    a = k * scale                                    # mm → px
    e = tx_cell + (-ink_x0 * k + (cell - ink_w_u) / 2) * scale
    f = (WIN_TOP - CAP_HEIGHT - row_top_mm * k) * scale
    transform = f"matrix({a:.6f},0,0,{a:.6f},{e:.3f},{f:.3f})"

    fy1 = (WIN_TOP - WIN_BOTTOM) * scale
    frame = f"  <!-- frame x={tx_cell:.3f},{tx_cell + cell * scale:.3f} y=0.000,{fy1:.3f} -->\n"
    body = "".join(f'    <path d="{d}" fill="#000000" fill-rule="evenodd"/>\n' for d in paths)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg"\n'
        f'     viewBox="0 0 {VIEWBOX} {VIEWBOX}"\n'
        f'     width="{VIEWBOX}" height="{VIEWBOX}">\n'
        f"  <title>PenchantManufacture-CJK {char}</title>\n"
        f"{frame}"
        f'  <g transform="{transform}">\n'
        f"{body}"
        "  </g>\n"
        "</svg>\n"
    )


def _verify(page: object, char: str, paths: list[str],
            ink: tuple[float, float, float, float]) -> float:
    """MuPDF が描いた原本のラスタと、自前 SVG（evenodd）のラスタの不一致率を返す。

    穴の埋まり・欠け・向きの取り違えを機械的に検出する唯一のチェック。
    """
    s = 8  # px/mm
    pad = 0.5
    x0, y0, x1, y1 = ink[0] - pad, ink[1] - pad, ink[2] + pad, ink[3] + pad
    clip = pymupdf.Rect(x0 / PT_TO_MM, y0 / PT_TO_MM, x1 / PT_TO_MM, y1 / PT_TO_MM)
    pix = page.get_pixmap(clip=clip, dpi=round(25.4 * s), colorspace="gray")
    ref = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w) < 128
    body = "".join(f'<path d="{d}" fill-rule="evenodd"/>' for d in paths)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1 - x0} {y1 - y0}" '
           f'width="{pix.w}" height="{pix.h}">{body}</svg>')
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=pix.w, output_height=pix.h,
                           background_color="white")
    mine = np.asarray(Image.open(BytesIO(png)).convert("L")) < 128
    # 輪郭 1px の差（ラスタライザ差・丸め）は捨て、面で残る差＝穴の埋まり／欠けだけ数える
    core = binary_erosion(ref ^ mine, iterations=1)
    return float(core.mean())


def extract_all(ai_path: Path = AI_PATH, out_dir: Path = OUT_DIR,
                dry_run: bool = False) -> list[Path]:
    """アートボードの全パスをセルへ割り当て、文字ごとに SVG を書き出す。"""
    page = pymupdf.open(str(ai_path))[ARTBOARD]
    cells: dict[tuple[int, int, int], list] = defaultdict(list)
    stray = 0
    for d in page.get_drawings():
        if d.get("fill") is None:
            continue
        r = d["rect"]
        loc = _locate(r.x0 * PT_TO_MM, r.y0 * PT_TO_MM)
        if loc is None:
            stray += 1
            continue
        gi, char, row, col = loc
        cells[(gi, row, col)].append(d)

    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
    produced: list[Path] = []
    for (gi, row, col), ds in sorted(cells.items()):
        name, _x0, y0, _px, py, cell, rows = GRID[gi]
        char = rows[row][col] if col < len(rows[row]) else ""
        if not char:
            print(f"  WARN: {name} 行{row} 列{col} に行文字列の割り当てがありません（{len(ds)}パス）")
            continue
        ink = (min(d["rect"].x0 for d in ds) * PT_TO_MM, min(d["rect"].y0 for d in ds) * PT_TO_MM,
               max(d["rect"].x1 for d in ds) * PT_TO_MM, max(d["rect"].y1 for d in ds) * PT_TO_MM)
        paths = [_path_d(d["items"], d["closePath"]) for d in ds]
        mismatch = _verify(page, char, paths, ink)
        if mismatch > 0.0:
            print(f"  WARN: {char} の描画が原本と {mismatch:.2%} 不一致（穴・重なりを確認）")
        svg = glyph_svg(char, paths, ink, y0 + row * py, cell)
        cp = ord(char)
        out_path = out_dir / f"char_uni{cp:04X}_{cp:04X}.svg"
        produced.append(out_path)
        tag = "DRY-RUN" if dry_run else "OK"
        print(f"  {tag}: {out_path.name}  {char} ({name} r{row} c{col}, {len(ds)}パス, 枠{cell}u)")
        if not dry_run:
            out_path.write_text(svg, encoding="utf-8")
    if stray:
        print(f"  WARN: グリッド外のパス {stray} 件を無視しました")
    print(f"\nCJK グリフ {len(produced)} 字")
    return produced


@click.command()
@click.option("--ai", "ai_path", default=str(AI_PATH), show_default=True, help=".ai 原本のパス")
@click.option("--out-dir", default=str(OUT_DIR), show_default=True, help="SVG 出力ディレクトリ")
@click.option("--dry-run", is_flag=True, help="ファイルを生成せず対象を表示")
def main(ai_path: str, out_dir: str, dry_run: bool) -> None:
    """Illustrator 原本の CJK アートボードを等幅グリフ SVG 化します。"""
    print(f"原本   : {ai_path}\n出力先 : {out_dir}\n")
    extract_all(Path(ai_path), Path(out_dir), dry_run=dry_run)


if __name__ == "__main__":
    main()
