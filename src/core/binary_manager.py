"""yt-dlp、ffmpeg、aria2c バイナリの確認とインストールを行う。

インストール方式:
  Windows : winget
  Linux   : yt-dlp/ffmpeg は curl（GitHubリリース）→ /usr/local/bin へ pkexec でインストール;
            aria2c はシステムパッケージマネージャ
"""
from __future__ import annotations

import shutil
import stat
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional

import requests

from .config import Config
from .platform_detector import PlatformInfo

# アプリの動作に必須のバイナリ
REQUIRED = ["yt-dlp", "ffmpeg"]
# オプションのバイナリ（aria2c）
OPTIONAL = ["aria2c"]

# Linux 向けの直接ダウンロードURL（curl）
_DL_URLS: Dict[str, Dict[str, str]] = {
    "yt-dlp": {
        "x86_64": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp",
        "aarch64": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux_aarch64",
    },
    "ffmpeg": {
        "x86_64": (
            "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
            "ffmpeg-master-latest-linux64-gpl.tar.xz"
        ),
        "aarch64": (
            "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
            "ffmpeg-master-latest-linuxarm64-gpl.tar.xz"
        ),
    },
}

# winget パッケージID
_WINGET_IDS: Dict[str, str] = {
    "yt-dlp": "yt-dlp.yt-dlp",
    "ffmpeg": "Gyan.FFmpeg",
    "aria2c": "aria2.aria2",
}

_CONFIG_KEYS: Dict[str, str] = {
    "yt-dlp": "YtdlpPath",
    "ffmpeg": "FfmpegPath",
    "aria2c": "Aria2cPath",
}

SYSTEM_BIN = Path("/usr/local/bin")

ProgressCallback = Callable[[int], None]  # 0-100


class BinaryManager:
    def __init__(self, config: Config, platform: PlatformInfo) -> None:
        self._config = config
        self._platform = platform

    # ------------------------------------------------------------------
    # 検索
    # ------------------------------------------------------------------

    def find(self, name: str) -> Optional[str]:
        """バイナリの絶対パスを返す。見つからない場合は None を返す。"""
        key = _CONFIG_KEYS[name]
        configured = self._config.get(key, "")
        if configured and Path(configured).is_file():
            return configured
        found = shutil.which(name)
        if found:
            self._config.set(key, found)
        return found

    def get_missing(self, include_optional: bool = False) -> List[str]:
        names = REQUIRED + (OPTIONAL if include_optional else [])
        return [n for n in names if not self.find(n)]

    # ------------------------------------------------------------------
    # インストール
    # ------------------------------------------------------------------

    def install(
        self,
        name: str,
        progress: Optional[ProgressCallback] = None,
    ) -> Optional[str]:
        """バイナリを自動インストールする。成功時はパスを返す。"""
        if self._platform.is_windows:
            return self._install_winget(name)
        if self._platform.is_linux:
            return self._install_linux(name, progress)
        raise RuntimeError(
            f"自動インストールは Windows と Linux のみ対応しています（現在の OS: {self._platform.display_name}）。"
            f"\n手動で {name} をインストールしてください。"
        )

    # ------------------------------------------------------------------
    # Windows 用
    # ------------------------------------------------------------------

    def _install_winget(self, name: str) -> Optional[str]:
        wid = _WINGET_IDS.get(name)
        if not wid:
            raise ValueError(f"No winget ID for {name}")
        cmd = [
            "winget", "install", "--id", wid, "-e", "--silent",
            "--accept-source-agreements", "--accept-package-agreements",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout)
        path = shutil.which(name)
        if path:
            self._config.set(_CONFIG_KEYS[name], path)
        return path

    # ------------------------------------------------------------------
    # Linux 用
    # ------------------------------------------------------------------

    def _install_linux(
        self, name: str, progress: Optional[ProgressCallback]
    ) -> Optional[str]:
        if name == "yt-dlp":
            return self._curl_binary("yt-dlp", self._ytdlp_url(), progress)
        if name == "ffmpeg":
            return self._install_ffmpeg_linux(progress)
        if name == "aria2c":
            return self.install_aria2c_linux()
        raise ValueError(f"Unknown binary: {name}")

    def _ytdlp_url(self) -> str:
        arch = "aarch64" if self._platform.is_arm64 else "x86_64"
        return _DL_URLS["yt-dlp"][arch]

    def _ffmpeg_url(self) -> str:
        arch = "aarch64" if self._platform.is_arm64 else "x86_64"
        return _DL_URLS["ffmpeg"][arch]

    def _pkexec_install_to_system(self, src: Path, name: str) -> str:
        """pkexec を使って src を /usr/local/bin/<name> にインストールする。

        Polkit の GUI 権限昇格ダイアログが表示されるため、
        GUI アプリからでも安全に root 権限を要求できる。
        pkexec が存在しない場合は RuntimeError を投げる。
        """
        pkexec = shutil.which("pkexec")
        if pkexec is None:
            raise RuntimeError(
                "pkexec が見つかりません。\n"
                f"ターミナルで手動インストールしてください:\n"
                f"  sudo install -m 755 {src} {SYSTEM_BIN / name}"
            )

        dest = SYSTEM_BIN / name
        result = subprocess.run(
            [pkexec, "install", "-m", "755", "-o", "root", "-g", "root",
             str(src), str(dest)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                result.stderr or result.stdout or f"{name} のインストールに失敗しました。"
            )
        return str(dest)

    def _curl_binary(
        self,
        name: str,
        url: str,
        progress: Optional[ProgressCallback],
    ) -> str:
        """HTTP経由で単一の実行可能バイナリをダウンロードし、/usr/local/bin にインストールする。"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{name}") as tmp:
            tmp_path = Path(tmp.name)

        try:
            _download_file(url, tmp_path, progress)
            _make_executable(tmp_path)
            dest = self._pkexec_install_to_system(tmp_path, name)
        finally:
            tmp_path.unlink(missing_ok=True)

        self._config.set(_CONFIG_KEYS[name], dest)
        return dest

    def _install_ffmpeg_linux(
        self, progress: Optional[ProgressCallback]
    ) -> Optional[str]:
        url = self._ffmpeg_url()

        with tempfile.NamedTemporaryFile(suffix=".tar.xz", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            # ダウンロード（進捗 0〜70% を報告）
            _download_file(url, tmp_path, _scale_progress(progress, 0, 70))

            if progress:
                progress(75)

            # ffmpeg バイナリのみを一時ディレクトリに展開
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_ffmpeg = Path(tmpdir) / "ffmpeg"
                with tarfile.open(tmp_path, "r:xz") as tar:
                    for member in tar.getmembers():
                        if Path(member.name).name == "ffmpeg" and member.isfile():
                            member.name = "ffmpeg"
                            tar.extract(member, path=tmpdir, filter="data")
                            break
                    else:
                        raise RuntimeError("ffmpeg binary not found inside archive")

                _make_executable(tmp_ffmpeg)

                if progress:
                    progress(90)

                # pkexec で /usr/local/bin へインストール（GUI 権限昇格）
                dest = self._pkexec_install_to_system(tmp_ffmpeg, "ffmpeg")

            self._config.set(_CONFIG_KEYS["ffmpeg"], dest)
            if progress:
                progress(100)
            return dest
        finally:
            tmp_path.unlink(missing_ok=True)

    def _pkg_manager(self, package: str) -> Optional[List[str]]:
        """インストールに使えるパッケージマネージャを検出し、コマンドを返す。

        sudo を伴う実際のインストールは GUI 側で pkexec 等を介して行うため、
        ここではコマンドリストを返すだけにとどめる。
        """
        managers = [
            ("apt-get", ["apt-get", "install", "-y", package]),
            ("dnf",     ["dnf",     "install", "-y", package]),
            ("pacman",  ["pacman",  "-S", "--noconfirm", package]),
            ("zypper",  ["zypper",  "install", "-y", package]),
        ]
        for mgr_bin, cmd in managers:
            if shutil.which(mgr_bin):
                return cmd
        return None

    def install_aria2c_linux(self) -> Optional[str]:
        """pkexec 経由で aria2c をインストールする。成功時はパスを返す。

        GUI アプリから sudo を直接呼ぶとパスワード入力待ちでハングするため、
        Polkit の pkexec を使って GUI 特権昇格ダイアログを起動する。
        pkexec が存在しない場合は RuntimeError を投げ、呼び出し元が
        手動インストールを促すダイアログを表示する。
        """
        cmd = self._pkg_manager("aria2")
        if cmd is None:
            raise RuntimeError(
                "対応するパッケージマネージャが見つかりませんでした。\n"
                "ターミナルで手動インストールしてください（例: sudo apt-get install aria2）。"
            )

        pkexec = shutil.which("pkexec")
        if pkexec is None:
            raise RuntimeError(
                "pkexec が見つかりません。\n"
                "ターミナルで手動インストールしてください（例: sudo apt-get install aria2）。"
            )

        result = subprocess.run(
            [pkexec] + cmd,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or "インストールに失敗しました。")

        path = shutil.which("aria2c")
        if path:
            self._config.set(_CONFIG_KEYS["aria2c"], path)
        return path


# ------------------------------------------------------------------
# ヘルパー関数
# ------------------------------------------------------------------

def _download_file(
    url: str,
    dest: Path,
    progress: Optional[ProgressCallback],
    timeout: int = 120,
) -> None:
    response = requests.get(url, stream=True, timeout=timeout)
    response.raise_for_status()
    total = int(response.headers.get("content-length", 0))
    downloaded = 0
    with dest.open("wb") as fh:
        for chunk in response.iter_content(chunk_size=65_536):
            fh.write(chunk)
            downloaded += len(chunk)
            if progress and total:
                progress(int(downloaded / total * 100))
    if progress:
        progress(100)


def _make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _scale_progress(
    cb: Optional[ProgressCallback], lo: int, hi: int
) -> Optional[ProgressCallback]:
    if cb is None:
        return None
    return lambda pct: cb(lo + int(pct * (hi - lo) / 100))
