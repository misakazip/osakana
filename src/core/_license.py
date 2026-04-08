# LICENSE ファイルを読み込んで本文を返す。
#
# 通常実行時は src/core/_license.py から 2 階層上 (プロジェクトルート) の
# LICENSE を参照し、PyInstaller 実行時は sys._MEIPASS に展開された
# バンドルを参照する。どちらも見つからない場合はフォールバック文字列を返す。
from __future__ import annotations

import sys
from pathlib import Path

_FALLBACK = "(LICENSE ファイルが見つかりませんでした)"


def _find_license() -> Path | None:
    # LICENSE ファイルのパスを探す。見つからなければ None。
    # PyInstaller バンドルを優先
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bundled = Path(meipass) / "LICENSE"
        if bundled.is_file():
            return bundled

    # 開発環境: src/core/_license.py → src/core → src → project_root
    source = Path(__file__).parent.parent.parent / "LICENSE"
    if source.is_file():
        return source

    return None


def _load() -> str:
    path = _find_license()
    if path is None:
        return _FALLBACK
    return path.read_text(encoding="utf-8")


LICENSE_TEXT: str = _load()
