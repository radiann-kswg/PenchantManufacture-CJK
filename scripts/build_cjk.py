"""PenchantManufacture-CJK 等幅ビルド（欧文 OTF ＋ Illustrator .ai → SVG → CJK decal PNG）。

本家スクリプト（``.EN-original/scripts``）を import して再利用し、CJK 側の差分だけをここに置く:

    1. latin   本家 ``extract_glyphs.extract_all`` で OTF を SVG 化 → transform/frame を
               等幅枠（半角 496u / 全角 992u）へ書き換える
    2. cjk     ``extract_ai_glyphs`` で .ai アートボードを SVG 化（同じ枠契約）
    3. decal   本家 ``generate_decal`` の render を CJK グリフだけに適用（5 スキーム）
    4. weekday 曜日漢字 7 字を曜日配色（docs/WEEKDAY_COLORING_PLAN.md）でデカール化
    5. previews README 用プレビュー（docs/previews/hero.png, glyphset.png）

使い方（Windows は ``py -3.14``。libcairo が無ければ ``$env:CAIRO_DLL_DIR`` で DLL の場所を渡す。
macOS は venv の ``python`` に読み替え、Homebrew の libcairo は
``DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`` で見つけさせる）:
    py -3.14 scripts/build_cjk.py
    py -3.14 scripts/build_cjk.py --no-decal        # SVG だけ更新
    py -3.14 scripts/build_cjk.py --font ... --ai ...
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import click
from fontTools import ttLib
from fontTools.pens.boundsPen import BoundsPen

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".EN-original" / "scripts"))
sys.path.insert(0, str(ROOT / "scripts"))
# Windows: cairosvg（本家 decal）が使う libcairo の DLL は pip では入らない。
# 手元にある DLL のディレクトリ（例: KiCad の bin）を CAIRO_DLL_DIR で渡す。
if os.environ.get("CAIRO_DLL_DIR"):
    os.environ["PATH"] = os.environ["CAIRO_DLL_DIR"] + os.pathsep + os.environ["PATH"]

import extract_glyphs as eg  # noqa: E402  本家
import generate_decal as gd  # noqa: E402  本家
import extract_ai_glyphs as ai  # noqa: E402

FONT = ROOT / "_original-fonts" / "penchant-manufacture_v4.0-release" / "PenchantManufacture.otf"
SRC = ROOT / "src" / "glyphs"
DIST = ROOT / "dist" / "glyphs_decal"
DIST_SQUARE = ROOT / "dist" / "glyphs_decal_square"
ALIASES = ROOT / "docs" / "glyph_aliases.json"

CELL_HALF, CELL_FULL = ai.CELL_HALF, ai.CELL_FULL
_TX_RE = re.compile(r'(transform="matrix\([-\d.]+,0,0,[-\d.]+,)([-\d.]+)(,[-\d.]+\)")')
_FRAME_RE = re.compile(r"<!-- frame x=[-\d.]+,[-\d.]+ (y=[-\d.]+,[-\d.]+) -->")

# 曜日配色（docs/WEEKDAY_COLORING_PLAN.md）: 字 → (塗り, 縁取り)
WEEKDAY: dict[str, tuple[str, str]] = {
    "日": ("#FF0033", "#990000"),
    "月": ("#9933FF", "#660099"),
    "火": ("#FF6600", "#993300"),
    "水": ("#336666", "#99CCCC"),
    "木": ("#00CC99", "#006633"),
    "金": ("#FFFF99", "#996600"),
    "土": ("#3366CC", "#003366"),
}


def _rgb(hex_color: str) -> tuple[int, int, int]:
    return tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def monospace_latin(font_path: Path, out_dir: Path) -> list[Path]:
    """本家 extract → 各 SVG を等幅枠へ（判定はインク幅、配置は advance 中央／超過時インク中央）。"""
    produced = eg.extract_all(font_path, out_dir, aliases_path=ALIASES, prune=False)
    tt = ttLib.TTFont(str(font_path))
    glyph_set = tt.getGlyphSet()
    hmtx = tt["hmtx"].metrics
    scale = ai.VIEWBOX / ai.UPM
    glyphs = json.loads(ALIASES.read_text(encoding="utf-8"))["glyphs"]

    for svg_path in produced:
        info = glyphs[svg_path.stem]
        adv = hmtx[info["glyph"]][0]
        pen = BoundsPen(glyph_set)
        glyph_set[info["glyph"]].draw(pen)
        ink_x0, _, ink_x1, _ = pen.bounds
        ink_w = ink_x1 - ink_x0
        cell = CELL_HALF if ink_w <= CELL_HALF else CELL_FULL
        if ink_w > CELL_FULL:
            print(f"  WARN: {info['char']} のインク幅 {ink_w:.0f}u が全角枠 {CELL_FULL}u を超過"
                  "（フォント側で調整後に再ビルド）")
        # 枠内オフセット（u）: advance が枠に収まれば advance 中央、超えればインク中央
        gx = (cell - adv) / 2 if adv <= cell else (cell - ink_w) / 2 - ink_x0
        tx_cell = (ai.VIEWBOX - cell * scale) / 2
        text = svg_path.read_text(encoding="utf-8")
        text = _TX_RE.sub(lambda m: f"{m.group(1)}{tx_cell + gx * scale:.3f}{m.group(3)}", text, count=1)
        text = _FRAME_RE.sub(
            lambda m: f"<!-- frame x={tx_cell:.3f},{tx_cell + cell * scale:.3f} {m.group(1)} -->",
            text, count=1)
        svg_path.write_text(text, encoding="utf-8")
    return produced


def decal(sources: list[Path], schemes: dict[str, gd.Scheme]) -> int:
    """本家 render をそのまま使い、指定グリフだけをデカール化する（描画一致統合は行わない）。"""
    count = 0
    for key, scheme in schemes.items():
        print(f"[{key}] {scheme.label} → {DIST / key}")
        for svg in sources:
            img = gd.render(gd.load_mask(svg), scheme, gd._seed_for(svg.stem + key))
            gd._save_all_sizes(img, DIST / key, svg.stem, gd.frame_box(svg),
                               square_dir=DIST_SQUARE / key)
            count += 1
    return count


def build(font_path: Path, ai_path: Path, with_decal: bool) -> None:
    print("== 1/5 latin: OTF → 等幅 SVG")
    latin = monospace_latin(font_path, SRC)
    print("\n== 2/5 cjk: .ai → 等幅 SVG")
    cjk = ai.extract_all(ai_path, SRC)
    keep = {p.stem for p in latin + cjk}
    for stale in SRC.glob("char_*.svg"):
        if stale.stem not in keep:
            stale.unlink()
            print(f"  旧 SVG を削除: {stale.name}")
    _selfcheck(cjk)
    if not with_decal:
        return

    print("\n== 3/5 decal: CJK グリフ × 5 スキーム")
    n = decal(cjk, gd.SCHEMES)
    print("\n== 4/5 weekday: 曜日配色")
    by_char = {chr(int(p.stem[8:12], 16)): p for p in cjk}   # char_uniXXXX_XXXX
    for char, (fill, edge) in WEEKDAY.items():
        if char not in by_char:
            print(f"  WARN: {char} の SVG がありません")
            continue
        scheme = gd.Scheme(f"曜日 {char}", "mono", _rgb(fill), _rgb(fill), _rgb(edge), _rgb(edge),
                           _rgb(edge), grain=0.0)
        n += decal([by_char[char]], {"weekday": scheme})
    print("\n== 5/5 previews: README 用プレビュー")
    import build_previews_cjk  # noqa: E402  dist が揃ってから import
    build_previews_cjk.build()
    print(f"\n完了: 欧文 {len(latin)} 字 / CJK {len(cjk)} 字 / decal {n} 点")


def _selfcheck(cjk: list[Path]) -> None:
    """壊れたら即わかる最小チェック: 半角カナと全角かなの枠幅が契約どおりか。"""
    scale = ai.VIEWBOX / ai.UPM
    for stem, cell in (("char_uniFF71_FF71", CELL_HALF), ("char_uni3044_3044", CELL_FULL)):
        path = SRC / f"{stem}.svg"
        assert path.exists(), f"{stem} が生成されていません（GRID を確認）"
        x0, x1, _, _ = map(float, gd._FRAME_RE.search(path.read_text(encoding="utf-8")).groups())
        assert abs((x1 - x0) - cell * scale) < 0.01, f"{stem} の枠幅が {cell}u ではありません"


@click.command()
@click.option("--font", "font_path", default=str(FONT), show_default=True, help="欧文 OTF")
@click.option("--ai", "ai_path", default=str(ai.AI_PATH), show_default=True, help="CJK .ai 原本")
@click.option("--no-decal", is_flag=True, help="SVG のみ更新（PNG を生成しない）")
def main(font_path: str, ai_path: str, no_decal: bool) -> None:
    """欧文 OTF と Illustrator 原本から等幅グリフ SVG と CJK デカール PNG を生成します。"""
    build(Path(font_path), Path(ai_path), with_decal=not no_decal)


if __name__ == "__main__":
    main()
