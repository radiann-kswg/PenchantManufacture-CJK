"""Fusion 360 Text Commands (Py) 用: 全スケッチを固定フォルダへ DXF 書き出しする。

Text Commands パレット（Py モード）で以下を実行:
    exec(open(r"C:\\Visual Studio Code UserFile\\ImageAssets\\PenchantManufacture-CJK\\scripts\\fusion\\export_dxf_textcmd.py", encoding="utf-8").read())

ダイアログを一切出さず、`assets/sketches/dxf/_raw/` へ
`{コンポーネント名}_{スケッチ名}.dxf` として書き出す。
"""

import os
import re

import adsk.core  # type: ignore
import adsk.fusion  # type: ignore

_OUT_DIR = r"C:\Visual Studio Code UserFile\ImageAssets\PenchantManufacture-CJK\assets\sketches\dxf\_raw"


def _sanitize(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name).strip("_") or "unnamed"


def _export_all() -> str:
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return "NG: アクティブなデザインがありません"
    os.makedirs(_OUT_DIR, exist_ok=True)
    ok, ng = [], []
    for comp in design.allComponents:
        for sketch in comp.sketches:
            stem = f"{_sanitize(comp.name)}_{_sanitize(sketch.name)}"
            try:
                if sketch.saveAsDXF(os.path.join(_OUT_DIR, stem + ".dxf")):
                    ok.append(stem)
                else:
                    ng.append(stem)
            except Exception:  # noqa: BLE001
                ng.append(stem)
    return f"OK: {len(ok)} 件書き出し / 失敗 {len(ng)} 件 {ng if ng else ''}"


print(_export_all())
