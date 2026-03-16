"""yt-dlp および Osakana 本体のアップデートを確認する。"""
from __future__ import annotations

import subprocess
from typing import Optional

import requests

# PyPI の JSON API はレート制限がなく認証不要。
# GitHub API（60 req/h）の代替として使用する。
_YTDLP_API = "https://pypi.org/pypi/yt-dlp/json"

# Osakana の GitHub リリース API
_OSAKANA_API = "https://api.github.com/repos/misakazip/osakana/releases/latest"

# 現在のアプリバージョン（pyproject.toml の version と一致させる）
APP_VERSION = "0.0.2"


def _parse_version(v: str) -> tuple[int, ...]:
    """バージョン文字列を整数タプルに変換する（例: "v1.2.3" → (1, 2, 3)）。"""
    return tuple(int(x) for x in v.lstrip("v").split(".") if x.isdigit())


def _normalize(version: str) -> str:
    """yt-dlp バージョンのゼロパディング差異を吸収する。

    例: "2026.03.13" → "2026.3.13"、"2026.3.13" → "2026.3.13"
    """
    parts = version.split(".")
    return ".".join(str(int(p)) if p.isdigit() else p for p in parts)


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
            return _normalize(self.current_version()) != _normalize(self.latest_version())
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
        resp = requests.get(_YTDLP_API, timeout=10)
        resp.raise_for_status()
        return resp.json()["info"]["version"]


# ------------------------------------------------------------------
# Osakana 本体のアップデート確認
# ------------------------------------------------------------------

class OsakanaUpdater:
    """GitHub releases API を使って Osakana 本体の更新を確認する。"""

    def __init__(self, current: str = APP_VERSION) -> None:
        self._current = current
        self._latest: Optional[str] = None
        self._release_url: Optional[str] = None

    def current_version(self) -> str:
        return self._current

    def latest_version(self) -> str:
        if self._latest is None:
            self._fetch()
        return self._latest or self._current

    def release_url(self) -> str:
        """最新リリースの GitHub ページ URL を返す。"""
        if self._latest is None:
            self._fetch()
        return self._release_url or ""

    def needs_update(self) -> bool:
        try:
            return _parse_version(self.latest_version()) > _parse_version(self._current)
        except Exception:
            return False

    def _fetch(self) -> None:
        resp = requests.get(_OSAKANA_API, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        self._latest = data["tag_name"].lstrip("v")
        self._release_url = data["html_url"]
