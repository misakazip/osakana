# yt-dlp および Osakana 本体のアップデートを確認する。
from __future__ import annotations

import subprocess
from typing import Optional, Tuple

import requests

# ─────────────────────────────────────────────────────────────────────
# 定数
# ─────────────────────────────────────────────────────────────────────

# 現在のアプリバージョン (pyproject.toml の version と一致させる)
APP_VERSION = "0.0.4"

# PyPI の JSON API はレート制限がなく認証不要。
# GitHub API (60 req/h) の代替として使用する。
_YTDLP_API   = "https://pypi.org/pypi/yt-dlp/json"
_OSAKANA_API = "https://api.github.com/repos/misakazip/osakana/releases/latest"

_HTTP_TIMEOUT = 10


# ─────────────────────────────────────────────────────────────────────
# バージョン比較ヘルパー
# ─────────────────────────────────────────────────────────────────────

def _parse_version(v: str) -> Tuple[int, ...]:
    # "v1.2.3" → (1, 2, 3) のようにバージョン文字列を整数タプルに変換する。
    return tuple(int(x) for x in v.lstrip("v").split(".") if x.isdigit())


def _normalize(version: str) -> str:
    # yt-dlp バージョンのゼロパディング差異を吸収する。
    # 例: "2026.03.13" → "2026.3.13"
    parts = version.split(".")
    return ".".join(str(int(p)) if p.isdigit() else p for p in parts)


# ─────────────────────────────────────────────────────────────────────
# yt-dlp アップデータ
# ─────────────────────────────────────────────────────────────────────

class YtDlpUpdater:
    # yt-dlp -U を使ったアップデート確認と実行を担う。

    def __init__(self, ytdlp_path: str) -> None:
        self._path = ytdlp_path
        self._current: Optional[str] = None
        self._latest:  Optional[str] = None

    # ------------------------------------------------------------------
    # バージョン取得 (キャッシュ付き)
    # ------------------------------------------------------------------

    def current_version(self) -> str:
        if self._current is None:
            self._current = self._fetch_current()
        return self._current

    def latest_version(self) -> str:
        if self._latest is None:
            self._latest = self._fetch_latest()
        return self._latest

    def needs_update(self) -> bool:
        # 現在版と最新版が一致しない場合 True。エラー時は False。
        try:
            return _normalize(self.current_version()) != _normalize(self.latest_version())
        except Exception:
            return False

    # ------------------------------------------------------------------
    # アップデート実行
    # ------------------------------------------------------------------

    def do_update(self) -> bool:
        # yt-dlp -U を実行する。成功時のみ True。
        return self._run_self_update().returncode == 0

    def update_output(self) -> str:
        # yt-dlp -U を実行し、stdout + stderr を返す。
        result = self._run_self_update()
        return result.stdout + result.stderr

    # ------------------------------------------------------------------
    # 内部メソッド
    # ------------------------------------------------------------------

    def _run_self_update(self) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [self._path, "-U"],
            capture_output=True,
            text=True,
        )
        self._current = None  # 実行後はキャッシュを必ず破棄
        return result

    def _fetch_current(self) -> str:
        result = subprocess.run(
            [self._path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()

    def _fetch_latest(self) -> str:
        response = requests.get(_YTDLP_API, timeout=_HTTP_TIMEOUT)
        response.raise_for_status()
        return response.json()["info"]["version"]


# ─────────────────────────────────────────────────────────────────────
# Osakana 本体のアップデータ
# ─────────────────────────────────────────────────────────────────────

class OsakanaUpdater:
    # GitHub Releases API を使って Osakana 本体の更新を確認する。

    def __init__(self, current: str = APP_VERSION) -> None:
        self._current = current
        self._latest:      Optional[str] = None
        self._release_url: Optional[str] = None

    def current_version(self) -> str:
        return self._current

    def latest_version(self) -> str:
        if self._latest is None:
            self._fetch()
        return self._latest or self._current

    def release_url(self) -> str:
        # 最新リリースの GitHub ページ URL を返す。
        if self._latest is None:
            self._fetch()
        return self._release_url or ""

    def needs_update(self) -> bool:
        try:
            return _parse_version(self.latest_version()) > _parse_version(self._current)
        except Exception:
            return False

    def _fetch(self) -> None:
        response = requests.get(_OSAKANA_API, timeout=_HTTP_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        self._latest      = data["tag_name"].lstrip("v")
        self._release_url = data["html_url"]
