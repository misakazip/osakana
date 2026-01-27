"""~/.osakana_config ファイルの読み書きを行う。

フォーマット（1行に1エントリ）:
    # コメント
    Key: value

真偽値は "true" / "false" として保存される。
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .platform_detector import detect as detect_platform

CONFIG_PATH = Path.home() / ".osakana_config"

DEFAULTS: Dict[str, Any] = {
    "AutoInstall": False,
    "AutoUpdate": False,
    "IsAria2cEnabled": False,
    "Aria2cConnections": 16,
    "MaxParallelDownloads": 2,
    "OutputDirectory": str(Path.home() / "Downloads"),
    "FilenameTemplate": "%(title)s [%(id)s].%(ext)s",
    "YtdlpPath": "",
    "FfmpegPath": "",
    "Aria2cPath": "",
}


def _serialize(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _deserialize(raw: str) -> Any:
    s = raw.strip()
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    try:
        return int(s)
    except ValueError:
        return s


class Config:
    def __init__(self) -> None:
        self._data: Dict[str, Any] = DEFAULTS.copy()
        self._platform = detect_platform()
        if CONFIG_PATH.exists():
            self._load()
        else:
            self.save()

    # ------------------------------------------------------------------
    # 公開API
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def update(self, updates: Dict[str, Any]) -> None:
        self._data.update(updates)
        self.save()

    def save(self) -> None:
        header = [
            "# Osakana Config",
            f"# Platform: {self._platform.display_name}",
            f"# Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]
        body = [f"{k}: {_serialize(v)}" for k, v in self._data.items()]
        CONFIG_PATH.write_text("\n".join(header + body) + "\n", encoding="utf-8")
        # Windows ではドット始まりファイルが自動的に非表示にならないため
        # FILE_ATTRIBUTE_HIDDEN (0x02) を ctypes で付与する
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(str(CONFIG_PATH), 0x02)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------

    def _load(self) -> None:
        with CONFIG_PATH.open("r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if ":" in stripped:
                    key, _, value = stripped.partition(":")
                    key = key.strip()
                    if key in DEFAULTS:
                        self._data[key] = _deserialize(value)
