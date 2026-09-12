"""等幅 OTF（PenchantManufacture CJK Mono）を fontTools で直接組む（フェーズ2）。

    欧文  本家 OTF（v4.0-release）の CFF アウトラインをそのまま複製し、advance を
          496u / 992u に、アウトラインを枠内オフセット gx だけ平行移動する
          （SVG を経由しないので字形の劣化がない。規則は metrics.latin_cell）。
    CJK   src/glyphs/char_uni*.svg（evenodd）を読み、skia-pathops で向きを正規化
          （evenodd → nonzero、重なり除去）してから CFF 化する。
    追加  .notdef（半角の中空矩形）、U+3000 全角スペース（992u）。
          本家の advance 0 の制御グリフ（.null / CR / LF）は持ち込まない。

メトリクス（unitsPerEm 1000、win 帯 793/198、hhea・typo 660/−400、capHeight 661、
xHeight 462）は本家の値をそのまま使う（scripts/metrics.py）。GPOS kern は等幅なので
持ち込まない。head の created/modified は固定値なので、字形を変えなければ再ビルドは
バイト一致する（PNG と同じく、字形が変わったときだけ dist/fonts/ をコミットする）。

使い方（Windows は ``py -3.14``、macOS は venv の ``python``。libcairo は不要）:
    py -3.14 scripts/build_font.py              # dist/fonts/PenchantManufactureCJKMono-Regular.otf
    py -3.14 scripts/build_font.py --ttf        # TTF も併せて出力（直線のみなので無劣化）
    py -3.14 scripts/build_font.py --verify-only
通常は scripts/build_cjk.py のステップ 3/6 として実行される。
"""
from __future__ import annotations

import contextlib
import io
import re
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

import click
import numpy as np
import pathops
from fontTools import ttLib
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.timeTools import timestampFromString
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen, replayRecording
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.svgLib.path.parser import parse_path
from scipy.ndimage import binary_erosion

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".EN-original" / "scripts"))
sys.path.insert(0, str(ROOT / "scripts"))

import metrics as m  # noqa: E402

FONT = ROOT / "_original-fonts" / "penchant-manufacture_v4.0-release" / "PenchantManufacture.otf"
SRC = ROOT / "src" / "glyphs"
OUT_DIR = ROOT / "dist" / "fonts"

# ── 名前・版（docs/HANDOFF_PHASE2.md §4 で確定） ──
FAMILY = "PenchantManufacture CJK Mono"
STYLE = "Regular"
PS_NAME = "PenchantManufactureCJKMono-Regular"
VERSION = "0.1.0"                     # .ai v4.alpha1 に対応。字形を足したら上げる
COPYRIGHT = "© RadianN_kswg / ラジアン（柏木主税）"
DESIGNER = "RadianN_kswg"
URL = "https://www.numbertales-radiann.net"
LICENSE_TEXT = ("Creative Commons Attribution 4.0 International (CC BY 4.0). "
                "Attribution: RadianN_kswg. Embedding in software, documents and web pages "
                "is permitted; keep the author credit and a link to the license.")
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
BUILD_TIME = "Sat Sep 12 00:00:00 2026"   # head.created / modified（再現性のため固定）

DROP_GLYPHS = frozenset({".null", "controlLF", "controlCR"})   # advance 0 の制御グリフ
FULLWIDTH_SPACE = 0x3000

_TX_RE = re.compile(r'transform="matrix\(([-\d.]+),0,0,([-\d.]+),([-\d.]+),([-\d.]+)\)"')
_FRAME_RE = re.compile(r"<!-- frame x=([-\d.]+),([-\d.]+) y=([-\d.]+),([-\d.]+) -->")
_PATH_RE = re.compile(r'<path d="([^"]+)"')
# CJK の SVG ステム（char_uni3046_3046）。欧文の char_union_222A 等と区別する
_CJK_STEM_RE = re.compile(r"^char_uni([0-9A-F]{4})_\1$")


def cjk_codepoint(stem: str) -> int | None:
    """CJK ステムならコードポイント、欧文ステムなら None。"""
    mt = _CJK_STEM_RE.match(stem)
    return int(mt.group(1), 16) if mt else None


class Glyph(NamedTuple):
    """フォントに載せる 1 グリフ（アウトラインはフォント座標の RecordingPen 記録）。"""

    name: str
    advance: int
    outline: list
    exact: bool = True   # True: 座標を丸めない（本家 OTF 複製）。CJK は mm 由来なので整数へ丸める

    def bounds(self) -> tuple[float, float, float, float] | None:
        pen = BoundsPen(None)
        replayRecording(self.outline, pen)
        return pen.bounds


# ── グリフの収集 ──

def latin_glyphs(font_path: Path) -> tuple[list[Glyph], dict[int, str]]:
    """本家 OTF の全グリフを等幅枠へ平行移動して複製する（cmap もそのまま継承）。"""
    tt = ttLib.TTFont(str(font_path))
    glyph_set = tt.getGlyphSet()
    hmtx = tt["hmtx"].metrics
    glyphs: list[Glyph] = []
    for name in tt.getGlyphOrder():
        if name == ".notdef" or name in DROP_GLYPHS:
            continue
        adv = hmtx[name][0]
        bpen = BoundsPen(glyph_set)
        glyph_set[name].draw(bpen)
        if bpen.bounds is None:                       # space / nbsp / softhyphen
            glyphs.append(Glyph(name, m.CELL_HALF, []))
            continue
        ink_x0, _, ink_x1, _ = bpen.bounds
        if ink_x1 - ink_x0 > m.CELL_FULL:
            print(f"  WARN: {name} のインク幅 {ink_x1 - ink_x0:.0f}u が全角枠 {m.CELL_FULL}u を超過")
        cell, gx = m.latin_cell(adv, ink_x0, ink_x1)
        rec = RecordingPen()
        glyph_set[name].draw(TransformPen(rec, (1, 0, 0, 1, gx, 0)))
        glyphs.append(Glyph(name, cell, rec.value))
    cmap = {cp: g for cp, g in tt.getBestCmap().items() if g not in DROP_GLYPHS}
    return glyphs, cmap


def cjk_outline(svg_text: str) -> tuple[int, list]:
    """等幅 SVG（evenodd）→ (枠幅 u, nonzero 化したフォント座標アウトライン)。

    SVG px → u は ``u_x = (px_x − X0) / SCALE``、``u_y = WIN_TOP − px_y / SCALE``
    （X0 は ``<!-- frame -->`` の枠左端）。向きの正規化は skia-pathops に任せる
    （PyMuPDF 由来の矩形は周り方が当てにならないため、SVG 側は evenodd で逃げている）。
    """
    a, _, e, f = map(float, _TX_RE.search(svg_text).groups())
    x0, x1, _, _ = map(float, _FRAME_RE.search(svg_text).groups())
    cell = round((x1 - x0) / m.SCALE)
    path = pathops.Path()
    tpen = TransformPen(path.getPen(),
                        (a / m.SCALE, 0, 0, -a / m.SCALE, (e - x0) / m.SCALE, m.WIN_TOP - f / m.SCALE))
    for d in _PATH_RE.findall(svg_text):
        parse_path(d, tpen)
    path.fillType = pathops.FillType.EVEN_ODD
    path.simplify(fix_winding=True)          # → nonzero（外周が反時計回り = CFF 規約）
    rec = RecordingPen()
    path.draw(rec)
    return cell, rec.value


def cjk_glyphs(src_dir: Path) -> tuple[list[Glyph], dict[int, str]]:
    """``src/glyphs/char_uniXXXX_XXXX.svg`` を全部読む（欧文 SVG は使わない）。"""
    glyphs: list[Glyph] = []
    cmap: dict[int, str] = {}
    for svg in sorted(src_dir.glob("char_uni*.svg")):
        cp = cjk_codepoint(svg.stem)
        if cp is None:
            continue
        cell, outline = cjk_outline(svg.read_text(encoding="utf-8"))
        name = f"uni{cp:04X}"
        glyphs.append(Glyph(name, cell, outline, exact=False))
        cmap[cp] = name
    return glyphs, cmap


def notdef_glyph() -> Glyph:
    """半角枠の中空矩形（外周は反時計回り、内周は時計回り）。"""
    rec = RecordingPen()
    for (x0, y0, x1, y1), reverse in (((50, -150, 446, 745), False), ((110, -90, 386, 685), True)):
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        if reverse:
            pts.reverse()
        rec.moveTo(pts[0])
        for p in pts[1:]:
            rec.lineTo(p)
        rec.closePath()
    return Glyph(".notdef", m.CELL_HALF, rec.value)


def collect(font_path: Path, src_dir: Path) -> tuple[list[Glyph], dict[int, str]]:
    """グリフ順: .notdef → 本家順の欧文 → U+3000 → CJK（コードポイント順）。"""
    latin, cmap = latin_glyphs(font_path)
    cjk, cjk_cmap = cjk_glyphs(src_dir)
    assert FULLWIDTH_SPACE not in cmap and not (set(cmap) & set(cjk_cmap)), "cmap が衝突"
    cmap.update(cjk_cmap)
    cmap[FULLWIDTH_SPACE] = "uni3000"
    return [notdef_glyph(), *latin, Glyph("uni3000", m.CELL_FULL, []), *cjk], cmap


# ── フォントの組み立て ──

def build(font_path: Path = FONT, src_dir: Path = SRC, out_dir: Path = OUT_DIR,
          ttf: bool = False) -> Path:
    """OTF（``ttf=True`` なら TTF）を ``out_dir`` へ書き出し、そのパスを返す。"""
    glyphs, cmap = collect(font_path, src_dir)
    order = [g.name for g in glyphs]
    fb = FontBuilder(m.UPM, isTTF=ttf)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)

    if ttf:
        glyf = {}
        for g in glyphs:
            pen = TTGlyphPen(None)
            replayRecording(g.outline, ReverseContourPen(pen))   # TrueType は外周時計回り
            glyf[g.name] = pen.glyph()
        fb.setupGlyf(glyf)
    else:
        charstrings = {}
        for g in glyphs:
            pen = T2CharStringPen(g.advance, None, roundTolerance=0 if g.exact else 0.5)
            replayRecording(g.outline, pen)
            charstrings[g.name] = pen.getCharString()
        fb.setupCFF(PS_NAME, {
            # CFF の文字列は latin-1 限定なので日本語を含む COPYRIGHT は name テーブルだけに置く
            "version": VERSION, "Notice": f"© {DESIGNER}", "FullName": f"{FAMILY} {STYLE}",
            "FamilyName": FAMILY, "Weight": STYLE, "isFixedPitch": 1,
            "UnderlinePosition": -100, "UnderlineThickness": 50,
        }, charstrings, {})

    bounds = [b for g in glyphs if (b := g.bounds())]
    xmin, ymin = min(b[0] for b in bounds), min(b[1] for b in bounds)
    xmax, ymax = max(b[2] for b in bounds), max(b[3] for b in bounds)
    fb.setupHorizontalMetrics({g.name: (g.advance, round(b[0]) if (b := g.bounds()) else 0)
                               for g in glyphs})
    fb.setupHorizontalHeader(ascent=m.TYPO_ASCENDER, descent=m.TYPO_DESCENDER)
    fb.setupNameTable({
        "copyright": COPYRIGHT, "familyName": FAMILY, "styleName": STYLE,
        "uniqueFontIdentifier": f"{VERSION};{PS_NAME}", "fullName": f"{FAMILY} {STYLE}",
        "version": f"Version {VERSION}", "psName": PS_NAME,
        "manufacturer": DESIGNER, "designer": DESIGNER, "vendorURL": URL, "designerURL": URL,
        "description": ("Monospaced (halfwidth 496 / fullwidth 992 units) edition of "
                        "PenchantManufacture with kana and kanji, for terminals and code."),
        "licenseDescription": LICENSE_TEXT, "licenseInfoURL": LICENSE_URL,
    }, mac=False)
    fb.setupOS2(version=4, xAvgCharWidth=m.CELL_HALF, usWeightClass=400, usWidthClass=5, fsType=0,
                sTypoAscender=m.TYPO_ASCENDER, sTypoDescender=m.TYPO_DESCENDER, sTypoLineGap=0,
                usWinAscent=m.WIN_TOP, usWinDescent=-m.WIN_BOTTOM, fsSelection=0x40,
                sxHeight=m.X_HEIGHT, sCapHeight=m.CAP_HEIGHT)
    os2 = fb.font["OS/2"]
    os2.panose.bFamilyType, os2.panose.bProportion = 2, 9          # Text & Display / Monospaced
    os2.recalcUnicodeRanges(fb.font)
    os2.ulCodePageRange1 = 0b111 | (1 << 17)                      # Latin1/2・Cyrillic ＋ JIS(932)
    os2.ulCodePageRange2 = 0
    fb.setupPost(keepGlyphNames=ttf, isFixedPitch=1)
    ts = timestampFromString(BUILD_TIME)
    fb.setupHead(unitsPerEm=m.UPM, fontRevision=float(VERSION.rsplit(".", 1)[0]), flags=3,
                 created=ts, modified=ts, xMin=round(xmin), yMin=round(ymin),
                 xMax=round(xmax), yMax=round(ymax))
    fb.setupMaxp()

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{PS_NAME}.{'ttf' if ttf else 'otf'}"
    fb.save(str(out))
    print(f"  {out.relative_to(ROOT)}: {len(glyphs)} グリフ / cmap {len(cmap)} / {out.stat().st_size:,} bytes")
    return out


# ── 検証 ──

def _svg_contours(svg_text: str) -> list[np.ndarray]:
    """SVG の全 <path> を transform 適用済みの px 座標の閉多角形へ（直線のみが前提）。"""
    a, d_, e, f = map(float, _TX_RE.search(svg_text).groups())
    rec = RecordingPen()
    tpen = TransformPen(rec, (a, 0, 0, d_, e, f))
    for d in _PATH_RE.findall(svg_text):
        parse_path(d, tpen)
    contours: list[list[tuple[float, float]]] = []
    for op, args in rec.value:
        if op == "moveTo":
            contours.append([args[0]])
        elif op == "lineTo":
            contours[-1].append(args[0])
        elif op in ("closePath", "endPath"):
            continue
        else:
            raise AssertionError(f"直線以外のセグメント {op} は想定外")
    return [np.asarray(c, dtype=float) for c in contours if len(c) >= 3]


def _raster(contours: list[np.ndarray], size: int, nonzero: bool, scale: float = 2.0) -> np.ndarray:
    """走査線の winding 数で塗りを求める（nonzero / evenodd を厳密に区別する）。"""
    w = h = int(size * scale)
    diff = np.zeros((h, w + 1), np.int32)
    ys = np.arange(h) + 0.5
    for poly in contours:
        p = poly * scale
        for (x0, y0), (x1, y1) in zip(p, np.roll(p, -1, axis=0)):
            if y0 == y1:
                continue
            rows = np.nonzero((ys >= min(y0, y1)) & (ys < max(y0, y1)))[0]
            xs = x0 + (ys[rows] - y0) * (x1 - x0) / (y1 - y0)
            cols = np.clip(np.floor(xs - 0.5).astype(int) + 1, 0, w)
            np.add.at(diff, (rows, cols), 1 if y1 > y0 else -1)
    wind = np.cumsum(diff, axis=1)[:, :w]
    return wind != 0 if nonzero else (wind & 1) != 0


def _latin_stems(src_dir: Path) -> set[str]:
    return {p.stem for p in src_dir.glob("char_*.svg") if cjk_codepoint(p.stem) is None}


def verify(otf_path: Path, font_path: Path = FONT, src_dir: Path = SRC) -> list[str]:
    """フォントを開き直して契約を検査し、問題の一覧を返す（空なら合格）。

    1. 全グリフの advance ∈ {496, 992}、post.isFixedPitch
    2. cmap: 本家の全コードポイント（制御グリフ除く）＋ src の CJK ＋ U+3000
    3. 欧文: 本家 extract_glyphs で OTF から SVG を再抽出し、src/glyphs の欧文 SVG と
       frame・アウトライン座標が一致（SVG を経由せず複製した字形の検算）
    4. CJK: 再抽出 SVG（nonzero）と src の SVG（evenodd）のラスタが一致（穴の埋まりを検出）
    5. 「にほん」「ｺﾝﾃﾅ」の幅合計が 992×3 / 496×4
    """
    import extract_glyphs as eg  # noqa: E402  本家
    problems: list[str] = []
    tt = ttLib.TTFont(str(otf_path))
    cmap = tt.getBestCmap()
    hmtx = tt["hmtx"].metrics

    bad = {g: adv for g, (adv, _) in hmtx.items() if adv not in (m.CELL_HALF, m.CELL_FULL)}
    if bad:
        problems.append(f"advance が枠幅でないグリフ: {bad}")
    if not tt["post"].isFixedPitch:
        problems.append("post.isFixedPitch が 0")

    home = ttLib.TTFont(str(font_path)).getBestCmap()
    want = {cp for cp, g in home.items() if g not in DROP_GLYPHS}
    want |= {cp for p in src_dir.glob("char_uni*.svg") if (cp := cjk_codepoint(p.stem))} | {FULLWIDTH_SPACE}
    if set(cmap) != want:
        problems.append(f"cmap の過不足: 不足 {sorted(want - set(cmap))[:10]} 余分 {sorted(set(cmap) - want)[:10]}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        with contextlib.redirect_stdout(io.StringIO()):
            produced = eg.extract_all(otf_path, tmp_dir, aliases_path=tmp_dir / "aliases.json", prune=False)
        got = {p.stem: p.read_text(encoding="utf-8") for p in produced}
    if _latin_stems(src_dir) != {s for s in got if cjk_codepoint(s) is None}:
        problems.append("再抽出した欧文 SVG の集合が src/glyphs と一致しない")
    for stem, mine in sorted(got.items()):
        src = src_dir / f"{stem}.svg"
        if not src.exists():
            problems.append(f"{stem}: src/glyphs に無い")
            continue
        ref = src.read_text(encoding="utf-8")
        # frame の y（win 帯）は一致するはず。x は src 側が枠へ強制しているので、
        # 枠から左へはみ出す欧文（負のサイドベアリング）では再抽出側が広くなりうる → 比較しない
        if _FRAME_RE.search(mine).groups()[2:] != _FRAME_RE.search(ref).groups()[2:]:
            problems.append(f"{stem}: frame の y が不一致 {_FRAME_RE.search(mine).group(0)}")
        a, b = _svg_contours(mine), _svg_contours(ref)
        if cjk_codepoint(stem) is not None:
            xor = _raster(a, m.VIEWBOX, nonzero=True) ^ _raster(b, m.VIEWBOX, nonzero=False)
            if binary_erosion(xor, iterations=1).any():
                problems.append(f"{stem}: CJK のラスタが SVG と不一致 {xor.mean():.3%}（向き・穴を確認）")
        else:
            same = len(a) == len(b) and all(
                len(x) == len(y) and np.abs(x - y).max() < 0.02 for x, y in zip(a, b))
            if not same:
                problems.append(f"{stem}: 欧文アウトラインが SVG と不一致")

    for text, expect in (("にほん", m.CELL_FULL * 3), ("ｺﾝﾃﾅ", m.CELL_HALF * 4), ("Ⅷm ", m.CELL_FULL + m.CELL_HALF * 2)):
        width = sum(hmtx[cmap[ord(c)]][0] for c in text)
        if width != expect:
            problems.append(f"「{text}」の幅 {width}u ≠ {expect}u")
    return problems


def check(otf_path: Path, font_path: Path = FONT, src_dir: Path = SRC) -> None:
    problems = verify(otf_path, font_path, src_dir)
    for p in problems:
        print(f"  NG: {p}")
    if problems:
        raise SystemExit(f"検証 NG {len(problems)} 件: {otf_path}")
    print(f"  検証 OK: advance・cmap・欧文アウトライン・CJK ラスタ・幅合計 ({otf_path.name})")


@click.command()
@click.option("--font", "font_path", default=str(FONT), show_default=True, help="本家 OTF")
@click.option("--src", "src_dir", default=str(SRC), show_default=True, help="等幅 SVG のディレクトリ")
@click.option("--out-dir", default=str(OUT_DIR), show_default=True)
@click.option("--ttf", is_flag=True, help="TTF も出力する")
@click.option("--verify-only", is_flag=True, help="生成せず既存の OTF を検証する")
def main(font_path: str, src_dir: str, out_dir: str, ttf: bool, verify_only: bool) -> None:
    """本家 OTF と等幅 SVG から PenchantManufacture CJK Mono の OTF を生成・検証します。"""
    fp, sd, od = Path(font_path), Path(src_dir), Path(out_dir)
    if verify_only:
        check(od / f"{PS_NAME}.otf", fp, sd)
        return
    out = build(fp, sd, od)
    check(out, fp, sd)
    if ttf:
        build(fp, sd, od, ttf=True)


if __name__ == "__main__":
    main()
