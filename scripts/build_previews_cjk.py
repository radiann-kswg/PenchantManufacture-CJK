"""README 冒頭用のプレビュー画像を生成する（CJK 版）。

  docs/previews/hero.png     … 曜日漢字（weekday）＋ かな・カタカナ・半角カナの見本バナー
  docs/previews/glyphset.png … CJK 収録グリフ一覧（Unicode ブロック別・バリアント巡回）

本家 ``build_previews.py`` の ``load`` / ``flow`` を再利用し、入力は ``dist/glyphs_decal/`` の
生成済み PNG。``build_cjk.py`` の最終ステップとして呼ばれる（単体実行も可）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".EN-original" / "scripts"))
import build_previews as bp  # noqa: E402  本家（load / flow / 配色定数）

DIST = ROOT / "dist" / "glyphs_decal"
OUT = ROOT / "docs" / "previews"
VARIANTS = ["sumi", "patina", "nickel", "rust", "hazard"]

# hero の各行: (バリアント, 文字列)。収録済みの字だけで綴る
HERO_ROWS: tuple[tuple[str, str], ...] = (
    ("weekday", "日月火水木金土"),
    ("sumi", "にほん"),
    ("patina", "コンテナ"),
    ("nickel", "ｺﾝﾃﾅ"),
    ("rust", "年"),
)

BLOCKS: list[tuple[str, tuple[int, int]]] = [
    ("Hiragana  U+3040-309F", (0x3040, 0x309F)),
    ("Katakana  U+30A0-30FF", (0x30A0, 0x30FF)),
    ("Halfwidth Katakana  U+FF61-FF9F", (0xFF61, 0xFF9F)),
    ("CJK Unified Ideographs  U+4E00-9FFF", (0x4E00, 0x9FFF)),
]


def glyph(variant: str, ch: str, height: int) -> Image.Image | None:
    p = DIST / variant / f"char_uni{ord(ch):04X}_{ord(ch):04X}_512.png"
    return bp.load(p, height) if p.exists() else None


def build_hero(cell: int = 96, pad: int = 20, gap: int = 6, space: int = 40) -> None:
    """曜日漢字の行と、かな・カタカナ・半角カナの語を 1 枚のバナーに並べる。"""
    words = [[g for ch in text if (g := glyph(v, ch, cell))] for v, text in HERO_ROWS]
    words = [w for w in words if w]
    if not words:
        raise SystemExit("dist/glyphs_decal/ が空です。先に build_cjk.py を実行してください。")
    widths = [sum(g.width for g in w) + gap * (len(w) - 1) for w in words]
    # 1 行目（曜日）を上段、残りを下段に流す
    top, rest = widths[0], sum(widths[1:]) + space * (len(widths) - 2)
    W = pad * 2 + max(top, rest)
    s = Image.new("RGB", (W, pad * 2 + cell * 2 + space // 2), bp.BG)
    x = pad
    for g in words[0]:
        s.paste(g, (x, pad), g)
        x += g.width + gap
    x, y = pad, pad + cell + space // 2
    for w in words[1:]:
        for g in w:
            s.paste(g, (x, y), g)
            x += g.width + gap
        x += space - gap
    OUT.mkdir(parents=True, exist_ok=True)
    s.save(OUT / "hero.png")
    print("hero ->", OUT / "hero.png", s.size)


def build_glyphset(cell: int = 52, pad: int = 24, gap: int = 7, width: int = 1000) -> None:
    """CJK 収録グリフ一覧。ブロック毎にバリアントを巡回し、最後に曜日配色を載せる。"""
    entries: list[tuple[int, str]] = []
    for p in (DIST / VARIANTS[0]).glob("char_uni*_512.png"):
        m = re.search(r"_([0-9A-F]{4})_512\.png$", p.name)
        if m:
            entries.append((int(m.group(1), 16), p.name))
    blocks = [(label, [n for cp, n in sorted(entries) if lo <= cp <= hi])
              for label, (lo, hi) in BLOCKS]
    blocks = [(label, names) for label, names in blocks if names]
    weekday = [p for ch in "日月火水木金土"
               if (p := DIST / "weekday" / f"char_uni{ord(ch):04X}_{ord(ch):04X}_512.png").exists()]
    title_f, head_f, note_f = (ImageFont.load_default(size=s) for s in (34, 20, 15))
    head_h, sec_gap = 34, 26

    def render(sheet: Image.Image | None) -> int:
        draw = ImageDraw.Draw(sheet) if sheet else ImageDraw.Draw(Image.new("RGB", (1, 1)))
        y = pad
        if sheet:
            draw.text((pad, y), "PenchantManufacture-CJK  /  monospaced glyph set (alpha)",
                      font=title_f, fill=bp.TXT)
            draw.text((pad, y + 42),
                      f"{len(entries)} CJK glyphs  x  {len(VARIANTS)} variants "
                      f"({', '.join(VARIANTS)})  +  weekday coloring", font=note_f, fill=bp.SUB)
        y += 74
        for i, (label, names) in enumerate(blocks):
            variant = VARIANTS[i % len(VARIANTS)]
            paths = [DIST / variant / n for n in names]
            if sheet:
                draw.text((pad, y), f"{label}   [{variant}]  {len(paths)}", font=head_f, fill=bp.SUB)
            y += head_h + bp.flow(draw, sheet, paths, pad, y + head_h, width, cell, gap)
            y += sec_gap
        if weekday:
            if sheet:
                draw.text((pad, y), f"Weekday coloring   [weekday]  {len(weekday)}",
                          font=head_f, fill=bp.SUB)
            y += head_h + bp.flow(draw, sheet, weekday, pad, y + head_h, width, cell, gap)
        return y + pad

    height = render(None)
    sheet = Image.new("RGB", (width + pad * 2, height), bp.BG)
    render(sheet)
    OUT.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT / "glyphset.png")
    print("glyphset ->", OUT / "glyphset.png", sheet.size)


def build() -> None:
    build_hero()
    build_glyphset()


if __name__ == "__main__":
    build()
