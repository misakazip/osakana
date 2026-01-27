"""yt-dlp のアップデートを確認して適用する。"""
from __future__ import annotations

import re
import subprocess
from typing import Optional

import requests

_LATEST_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
_VERSION_RE = re.compile(r"\d{4}\.\d{2}\.\d{2}(?:\.\d+)?")


class YtDlpUpdater:
    def __init__(self, ytdlp_path: str) -> None:
        self._path = ytdlp_path
        self._current: Optional[str] = None
        self._latest: Optional[str] = None

    # ------------------------------------------------------------------
    # バージョン取得
    # ------------------------------------------------------------------

    def current_version(self) -> str:
        if self._current is None:
            self._current = self._get_current()
        return self._current

    def latest_version(self) -> str:
        if self._latest is None:
            self._latest = self._get_latest()
        return self._latest

    def needs_update(self) -> bool:
        try:
            return self.current_version() != self.latest_version()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # アップデート実行
    # ------------------------------------------------------------------

    def do_update(self) -> bool:
        """yt-dlp -U を実行し、成功時は True を返す。"""
        result = subprocess.run(
            [self._path, "-U"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            self._current = None  # キャッシュを無効化
        return result.returncode == 0

    def update_output(self) -> str:
        """yt-dlp -U を実行し、出力を結合して返す。"""
        result = subprocess.run(
            [self._path, "-U"],
            capture_output=True,
            text=True,
        )
        self._current = None
        return result.stdout + result.stderr

    # ------------------------------------------------------------------
    # 内部メソッド
    # ------------------------------------------------------------------

    def _get_current(self) -> str:
        result = subprocess.run(
            [self._path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()

    def _get_latest(self) -> str:
        resp = requests.get(_LATEST_API, timeout=10)
        resp.raise_for_status()
        tag = resp.json().get("tag_name", "")
        # 先頭の 'v' があれば除去する
        return tag.lstrip("v")
