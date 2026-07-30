"""Fusion 360 スクリプト: アクティブなデザインの全スケッチを DXF 書き出しする。

使い方:
    1. Fusion 360 で対象デザイン（例: Dice (NKO) v1）を開く
    2. ユーティリティ → アドイン → スクリプト → 「＋」で本フォルダを追加 → 実行
    3. 出力先フォルダを選択（例: PenchantManufacture-CJK/assets/sketches/dxf/_raw）

出力ファイル名は `{コンポーネント名}_{スケッチ名}.dxf`（記号はサニタイズ）。
グリフとの対応付け・`char_uniXXXX_XXXX.dxf` へのリネームは書き出し後に行う。
"""

import os
import re
import traceback

import adsk.core  # type: ignore
import adsk.fusion  # type: ignore


def _sanitize(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name).strip("_") or "unnamed"


def run(context):  # noqa: ANN001, ARG001
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox("アクティブなデザインがありません。")
            return

        dlg = ui.createFolderDialog()
        dlg.title = "DXF の出力先フォルダを選択"
        if dlg.showDialog() != adsk.core.DialogResults.DialogOK:
            return
        out_dir = dlg.folder

        exported, failed = [], []
        for comp in design.allComponents:
            for sketch in comp.sketches:
                stem = f"{_sanitize(comp.name)}_{_sanitize(sketch.name)}"
                path = os.path.join(out_dir, f"{stem}.dxf")
                try:
                    if sketch.saveAsDXF(path):
                        exported.append(stem)
                    else:
                        failed.append(stem)
                except Exception:  # noqa: BLE001
                    failed.append(stem)

        msg = f"DXF 書き出し完了: {len(exported)} 件\n出力先: {out_dir}"
        if failed:
            msg += "\n失敗: " + ", ".join(failed)
        ui.messageBox(msg)
    except Exception:  # noqa: BLE001
        if ui:
            ui.messageBox("エラー:\n{}".format(traceback.format_exc()))
