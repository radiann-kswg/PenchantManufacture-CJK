"""Dice (NKO) v1.f3d から かなグリフ輪郭を DXF 書き出しする。

Fusion 360 を使わず、.f3d 内の BRep バイナリ（ASM BinaryFile / .smbh 履歴
ストリーム）を直接パースして、サイコロ6面の彫り込みグリフ
「う」「お」「こ」「ち」「ま」「ん」の輪郭ループを抽出する。

- 全エッジは直線（straight-curve）のみ → LWPOLYLINE で無劣化出力
- 座標系: ASM 内部は cm。DXF は mm（$INSUNITS=4）で 10 倍して出力
- 面ごとの鏡像・回転補正は FACE_MAP に固定（目視同定済み）

実行:
    python scripts/extract_dice_dxf.py
出力:
    assets/sketches/dxf/char_uniXXXX_XXXX.dxf（6ファイル）
    assets/sketches/dxf/preview.png（検証用プレビュー）
"""
from __future__ import annotations

import io
import math
import struct
import zipfile
from pathlib import Path

import ezdxf

ROOT = Path(__file__).resolve().parent.parent
F3D_PATH = ROOT / "assets" / "fusion" / "Dice (NKO) v1.f3d"
OUT_DIR = ROOT / "assets" / "sketches" / "dxf"
SCALE = 10.0  # cm -> mm

# face_idx: (かな, コードポイント, 鏡像, 回転deg, グリフループの取り方)
# 同定根拠: 面609(お)のみ sense=False。sense=True の面は法線が面と逆向きのため
# 鏡像補正が必要。回転は目視で正立を確認済み。
FACE_MAP = {
    231: ("う", 0x3046, True, 90),
    609: ("お", 0x304A, False, 90),
    77: ("こ", 0x3053, True, 0),
    586: ("ち", 0x3061, True, 90),
    759: ("ま", 0x307E, True, 90),
    184: ("ん", 0x3093, True, 180),
}


class _Tok:
    """ASM BinaryFile のタグ付きトークン読み取り。"""

    def __init__(self, data: bytes, pos: int) -> None:
        self.d = data
        self.p = pos

    def u8(self) -> int:
        v = self.d[self.p]
        self.p += 1
        return v

    def i32(self) -> int:
        v = struct.unpack_from("<i", self.d, self.p)[0]
        self.p += 4
        return v

    def f64(self) -> float:
        v = struct.unpack_from("<d", self.d, self.p)[0]
        self.p += 8
        return v

    def str8(self) -> str:
        n = self.u8()
        s = self.d[self.p:self.p + n].decode("latin1")
        self.p += n
        return s


def _tokenize(data: bytes, start: int):
    t = _Tok(data, start)
    rec: list[tuple] = []
    while t.p < len(data):
        tag = t.u8()
        if tag == 0x11:
            yield rec
            rec = []
        elif tag == 0x04:
            rec.append(("i", t.i32()))
        elif tag == 0x06:
            rec.append(("d", t.f64()))
        elif tag == 0x07:
            rec.append(("s", t.str8()))
        elif tag == 0x08:
            n = struct.unpack_from("<H", t.d, t.p)[0]
            t.p += 2
            rec.append(("s", t.d[t.p:t.p + n].decode("latin1")))
            t.p += n
        elif tag == 0x0A:
            rec.append(("b", True))
        elif tag == 0x0B:
            rec.append(("b", False))
        elif tag == 0x0C:
            rec.append(("r", t.i32()))
        elif tag == 0x0D:
            rec.append(("id", t.str8()))
        elif tag == 0x0E:
            rec.append(("sub", t.str8()))
        elif tag in (0x0F, 0x10):
            rec.append(("brace", None))
        elif tag == 0x13:
            rec.append(("v3", (t.f64(), t.f64(), t.f64())))
        elif tag == 0x14:
            rec.append(("dir", (t.f64(), t.f64(), t.f64())))
        elif tag == 0x15:
            rec.append(("enum", t.i32()))
        elif tag == 0x02:
            rec.append(("c", t.u8()))
        elif tag == 0x03:
            v = struct.unpack_from("<h", t.d, t.p)[0]
            t.p += 2
            rec.append(("h", v))
        elif tag == 0x05:
            v = struct.unpack_from("<f", t.d, t.p)[0]
            t.p += 4
            rec.append(("f", v))
        else:
            raise ValueError(f"unknown tag 0x{tag:02x} at {t.p}")


def load_records(blob: bytes) -> list[list[tuple]]:
    """ASM BinaryFile ヘッダを読み飛ばし、全レコードを返す。"""
    i = blob.index(b"ASM BinaryFile") + len("ASM BinaryFile")
    t = _Tok(blob, i)
    t.p += 9
    t.i32()
    t.i32()
    for _ in range(3):
        assert t.u8() == 0x07
        t.str8()
    for _ in range(3):
        assert t.u8() == 0x06
        t.f64()
    return list(_tokenize(blob, t.p))


def _cname(r: list[tuple]) -> str:
    ids = [v for k, v in r if k == "id"]
    subs = [v for k, v in r if k == "sub"]
    return "-".join(subs + ids) if r else "?"


def _vals(r: list[tuple]) -> list:
    return [v for k, v in r if k not in ("id", "sub")]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def face_loops_2d(recs: list, fi: int) -> list[list[tuple[float, float]]]:
    """face のループ群を面ローカル 2D 座標（cm）の頂点列にして返す。"""

    def vpos(vi: int):
        for cand in _vals(recs[vi])[::-1]:
            if isinstance(cand, int) and 0 <= cand < len(recs) and _cname(recs[cand]) == "point":
                return _vals(recs[cand])[3]
        raise ValueError(f"vertex {vi}: point not found")

    f = _vals(recs[fi])
    li, si = f[4], f[7]
    sv = _vals(recs[si])
    origin, normal, uax = sv[3], sv[4], sv[5]
    vax = _cross(normal, uax)
    loops: list[list[tuple[float, float]]] = []
    seen_l: set[int] = set()
    while isinstance(li, int) and li >= 0 and li not in seen_l:
        seen_l.add(li)
        lr = _vals(recs[li])
        ce0 = lr[4]
        ce = ce0
        seen_c: set[int] = set()
        pts = []
        while isinstance(ce, int) and ce >= 0 and ce not in seen_c:
            seen_c.add(ce)
            cv = _vals(recs[ce])
            ev = _vals(recs[cv[6]])
            assert _cname(recs[ev[8]]) == "straight-curve", "直線以外のエッジは未対応"
            p0, p1 = vpos(ev[3]), vpos(ev[5])
            if cv[7] is False:
                p0, p1 = p1, p0
            pts.append(p0)
            ce = cv[3]
            if ce == ce0:
                break
        loops.append([(_dot(_sub(p, origin), uax), _dot(_sub(p, origin), vax)) for p in pts])
        li = lr[3]
    return loops


def _area(lp) -> float:
    n = len(lp)
    return abs(sum(lp[i][0] * lp[(i + 1) % n][1] - lp[(i + 1) % n][0] * lp[i][1]
                   for i in range(n))) / 2


def glyph_loops(recs: list, fi: int) -> list[list[tuple[float, float]]]:
    """外周（サイコロ面の正方形）を除いたグリフ輪郭ループのみ返す。"""
    loops = face_loops_2d(recs, fi)
    big = max(range(len(loops)), key=lambda i: _area(loops[i]))
    if len(loops[big]) <= 8:  # 単純外周（正方形等）→ 除外
        return [lp for i, lp in enumerate(loops) if i != big]
    return loops


def normalize(loops, mirror: bool, rot_deg: int, scale: float = SCALE):
    """鏡像→回転→原点合わせ→スケール。"""
    a = math.radians(rot_deg)
    ca, sa = math.cos(a), math.sin(a)
    out = []
    for lp in loops:
        q = []
        for x, y in lp:
            if mirror:
                x = -x
            q.append((x * ca - y * sa, x * sa + y * ca))
        out.append(q)
    minx = min(p[0] for lp in out for p in lp)
    miny = min(p[1] for lp in out for p in lp)
    return [[((p[0] - minx) * scale, (p[1] - miny) * scale) for p in lp] for lp in out]


def write_dxf(loops, path: Path) -> None:
    doc = ezdxf.new("R2000")
    doc.header["$INSUNITS"] = 4  # mm
    msp = doc.modelspace()
    for lp in loops:
        msp.add_lwpolyline(lp, close=True, dxfattribs={"layer": "GLYPH"})
    doc.saveas(path)


def main() -> None:
    with zipfile.ZipFile(F3D_PATH) as zf:
        name = next(n for n in zf.namelist() if n.endswith(".smbh"))
        blob = zf.read(name)
    recs = load_records(blob)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = {}
    for fi, (kana, cp, mirror, rot) in FACE_MAP.items():
        loops = normalize(glyph_loops(recs, fi), mirror, rot)
        stem = f"char_uni{cp:04X}_{cp:04X}"
        write_dxf(loops, OUT_DIR / f"{stem}.dxf")
        results[kana] = loops
        w = max(p[0] for lp in loops for p in lp)
        h = max(p[1] for lp in loops for p in lp)
        print(f"{kana} U+{cp:04X} face={fi} loops={len(loops)} {w:.2f}x{h:.2f}mm -> {stem}.dxf")

    # プレビュー
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.patches as mpatches
        import matplotlib.pyplot as plt
        from matplotlib.path import Path as MPath
        fig, axes = plt.subplots(1, len(results), figsize=(2.2 * len(results), 2.6))
        for ax, (kana, loops) in zip(axes, results.items()):
            verts, codes = [], []
            for lp in loops:
                verts += lp + [lp[0]]
                codes += [MPath.MOVETO] + [MPath.LINETO] * (len(lp) - 1) + [MPath.CLOSEPOLY]
            ax.add_patch(mpatches.PathPatch(MPath(verts, codes), facecolor="#222",
                                            edgecolor="none"))
            xs = [p[0] for p in verts]
            ys = [p[1] for p in verts]
            ax.set_xlim(min(xs) - 1, max(xs) + 1)
            ax.set_ylim(min(ys) - 1, max(ys) + 1)
            ax.set_aspect("equal")
            ax.axis("off")
            ax.set_title(kana)
        fig.savefig(OUT_DIR / "preview.png", dpi=120, bbox_inches="tight")
        print("preview:", OUT_DIR / "preview.png")
    except ImportError:
        print("matplotlib なし: プレビューをスキップ")


if __name__ == "__main__":
    main()
