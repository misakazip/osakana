"""LICENSE ファイルを読み込んで本文を返す。

通常実行時  : このファイルの2階層上（プロジェクトルート）の LICENSE を参照する。
PyInstaller : spec の datas でバンドルした LICENSE を sys._MEIPASS 経由で参照する。
どちらでも見つからない場合はフォールバックメッセージを返す。
"""
from __future__ import annotations

import sys
from pathlib import Path


def _find_license() -> Path | None:
    # PyInstaller 実行時: sys._MEIPASS に展開される
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        p = Path(meipass) / "LICENSE"
        if p.is_file():
            return p

    # 通常実行時: src/core/_license.py → src/core → src → project_root
    p = Path(__file__).parent.parent.parent / "LICENSE"
    if p.is_file():
        return p

    return None


def _load() -> str:
    path = _find_license()
    if path is None:
        return "(LICENSE ファイルが見つかりませんでした)"
    return path.read_text(encoding="utf-8")


LICENSE_TEXT: str = _load()
