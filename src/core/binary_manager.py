# yt-dlp / ffmpeg / aria2c バイナリの検出とインストールを行う。
#
# 設計方針:
#
# * yt-dlp と ffmpeg は GitHub Releases などから直接ダウンロードし、
#   ``~/.osakana/bin/`` 配下に保存する。アプリは常にこのローカルコピーを呼び出す。
# * aria2c はオプション機能のため、既存のシステム流儀に従う:
#     - Windows : winget
#     - Linux   : pkexec + パッケージマネージャ
#     - macOS   : Homebrew
from __future__ import annotations

import shutil
import stat
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Callable, Dict, List, Optional

import requests

from .config import Config
from .platform_detector import PlatformInfo

# ─────────────────────────────────────────────────────────────────────
# 定数
# ─────────────────────────────────────────────────────────────────────

# アプリの動作に必須のバイナリ
REQUIRED: List[str] = ["yt-dlp", "ffmpeg"]

# Osakana がローカル管理するバイナリ。これらは常に INSTALL_DIR から呼び出す。
_MANAGED = frozenset({"yt-dlp", "ffmpeg"})

# ローカルインストール先 (~/.osakana/bin)
INSTALL_DIR: Path = Path.home() / ".osakana" / "bin"

# ffmpeg バイナリ (Windows と Linux) を提供する BtbN ビルドのベース URL
_BTBN_BASE = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"

# yt-dlp 公式リリースのベース URL
_YTDLP_BASE = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/"

# Homebrew パッケージ名 (aria2c のみ使用)
_BREW_NAMES: Dict[str, str] = {"aria2c": "aria2"}

# winget パッケージ ID (aria2c のみ使用)
_WINGET_IDS: Dict[str, str] = {"aria2c": "aria2.aria2"}

# 設定ファイルのキー
_CONFIG_KEYS: Dict[str, str] = {
    "yt-dlp": "YtdlpPath",
    "ffmpeg": "FfmpegPath",
    "aria2c": "Aria2cPath",
}

# Linux で aria2 をインストールできるパッケージマネージャ候補
_LINUX_PKG_MANAGERS: List[List[str]] = [
    ["apt-get", "install", "-y", "aria2"],
    ["dnf",     "install", "-y", "aria2"],
    ["pacman",  "-S", "--noconfirm", "aria2"],
    ["zypper",  "install", "-y", "aria2"],
]

# 進捗コールバック (0–100)
ProgressCallback = Callable[[int], None]


# ─────────────────────────────────────────────────────────────────────
# URL / ローカルパス決定
# ─────────────────────────────────────────────────────────────────────

def _ytdlp_url(platform: PlatformInfo) -> str:
    # プラットフォーム別のシングルバイナリ配布物
    if platform.is_windows:
        return _YTDLP_BASE + "yt-dlp.exe"
    if platform.is_macos:
        return _YTDLP_BASE + "yt-dlp_macos"
    if platform.is_linux:
        return _YTDLP_BASE + ("yt-dlp_linux_aarch64" if platform.is_arm64 else "yt-dlp")
    raise RuntimeError(
        f"yt-dlp の配布物はこの OS には用意されていません: {platform.display_name}"
    )


def _ffmpeg_url(platform: PlatformInfo) -> str:
    # Windows: BtbN gpl ビルド (zip)
    if platform.is_windows:
        suffix = "winarm64-gpl.zip" if platform.is_arm64 else "win64-gpl.zip"
        return _BTBN_BASE + f"ffmpeg-master-latest-{suffix}"

    # Linux: BtbN gpl ビルド (tar.xz)
    if platform.is_linux:
        suffix = "linuxarm64-gpl.tar.xz" if platform.is_arm64 else "linux64-gpl.tar.xz"
        return _BTBN_BASE + f"ffmpeg-master-latest-{suffix}"

    # macOS: evermeet が単体バイナリ (zip) を提供
    if platform.is_macos:
        return "https://evermeet.cx/ffmpeg/getrelease/zip"

    raise RuntimeError(
        f"ffmpeg の配布物はこの OS には用意されていません: {platform.display_name}"
    )


def _local_filename(name: str, platform: PlatformInfo) -> str:
    # Windows のみ .exe 拡張子を付ける
    return f"{name}.exe" if platform.is_windows else name


# ─────────────────────────────────────────────────────────────────────
# BinaryManager
# ─────────────────────────────────────────────────────────────────────

class BinaryManager:
    # yt-dlp / ffmpeg / aria2c の検出とインストールを担うファサード。

    def __init__(self, config: Config, platform: PlatformInfo) -> None:
        self._config = config
        self._platform = platform
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 検出
    # ------------------------------------------------------------------

    def find(self, name: str) -> Optional[str]:
        # 管理対象 (yt-dlp / ffmpeg) は INSTALL_DIR のローカルコピーのみを参照する。
        # システム PATH 上の別バージョンが混入しないようにするため。
        if name in _MANAGED:
            return self._find_managed(name)
        return self._find_system(name)

    def _find_managed(self, name: str) -> Optional[str]:
        local = INSTALL_DIR / _local_filename(name, self._platform)
        if local.is_file():
            return self._save_path(name, str(local))
        # 旧設定のクリーンアップ: 過去にシステム PATH を保存していた場合は破棄する
        self._config.set(_CONFIG_KEYS[name], "")
        return None

    def _find_system(self, name: str) -> Optional[str]:
        # aria2c などのオプション依存はシステム PATH を尊重する
        configured = self._config.get(_CONFIG_KEYS[name], "")
        if configured and Path(configured).is_file():
            return configured

        found = shutil.which(name)
        if found:
            self._config.set(_CONFIG_KEYS[name], found)
        return found

    def get_missing(self) -> List[str]:
        # 必須バイナリのうち見つからないものを返す。
        return [name for name in REQUIRED if not self.find(name)]

    # ------------------------------------------------------------------
    # インストール (公開エントリーポイント)
    # ------------------------------------------------------------------

    def install(
        self,
        name: str,
        progress: Optional[ProgressCallback] = None,
    ) -> Optional[str]:
        # バイナリを自動インストールし、成功時はパスを返す。
        if name in _MANAGED:
            return self._install_managed(name, progress)
        return self._install_system(name)

    # ------------------------------------------------------------------
    # 管理バイナリ (yt-dlp / ffmpeg) の URL ダウンロード
    # ------------------------------------------------------------------

    def _install_managed(
        self, name: str, progress: Optional[ProgressCallback]
    ) -> str:
        if name == "yt-dlp":
            return self._install_ytdlp(progress)
        if name == "ffmpeg":
            return self._install_ffmpeg(progress)
        raise ValueError(f"未知の管理バイナリ: {name}")

    def _install_ytdlp(self, progress: Optional[ProgressCallback]) -> str:
        # 単一の実行ファイルなのでそのまま INSTALL_DIR に保存する。
        url = _ytdlp_url(self._platform)
        dest = INSTALL_DIR / _local_filename("yt-dlp", self._platform)

        _download_file(url, dest, progress)
        if not self._platform.is_windows:
            _make_executable(dest)

        self._config.set(_CONFIG_KEYS["yt-dlp"], str(dest))
        return str(dest)

    def _install_ffmpeg(self, progress: Optional[ProgressCallback]) -> str:
        # アーカイブをダウンロード → ffmpeg バイナリのみを INSTALL_DIR に展開する。
        url = _ffmpeg_url(self._platform)
        dest = INSTALL_DIR / _local_filename("ffmpeg", self._platform)

        # 拡張子はダウンロード後に zipfile で判定するため、suffix は付けなくても可。
        # ただし extract 側のヒントとして残しておく。
        suffix = ".zip" if (self._platform.is_windows or self._platform.is_macos) else ".tar.xz"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            archive_path = Path(tmp.name)

        try:
            # 0–80%: ダウンロード
            _download_file(url, archive_path, _scale_progress(progress, 0, 80))
            _emit(progress, 85)

            # 85–100%: 展開
            _extract_ffmpeg(archive_path, dest, _local_filename("ffmpeg", self._platform))
            if not self._platform.is_windows:
                _make_executable(dest)
            _emit(progress, 100)
        finally:
            archive_path.unlink(missing_ok=True)

        self._config.set(_CONFIG_KEYS["ffmpeg"], str(dest))
        return str(dest)

    # ------------------------------------------------------------------
    # システムバイナリ (aria2c) のインストール
    # ------------------------------------------------------------------

    def _install_system(self, name: str) -> Optional[str]:
        if self._platform.is_windows:
            return self._install_winget(name)
        if self._platform.is_linux:
            return self._install_aria2c_linux(name)
        if self._platform.is_macos:
            return self._install_brew(name)

        raise RuntimeError(
            f"自動インストールは Windows / Linux / macOS のみ対応しています "
            f"(現在の OS: {self._platform.display_name})。\n"
            f"手動で {name} をインストールしてください。"
        )

    def _install_winget(self, name: str) -> Optional[str]:
        winget_id = _WINGET_IDS.get(name)
        if not winget_id:
            raise ValueError(f"winget ID が定義されていません: {name}")

        _run_checked([
            "winget", "install",
            "--id", winget_id,
            "-e", "--silent",
            "--accept-source-agreements",
            "--accept-package-agreements",
        ])
        return self._save_path(name, shutil.which(name))

    def _install_aria2c_linux(self, name: str) -> Optional[str]:
        # GUI アプリから sudo を直接呼ぶとパスワード入力でハングするため、
        # Polkit の pkexec を使い GUI 特権昇格ダイアログを表示する。
        if name != "aria2c":
            raise ValueError(f"Linux 自動インストール非対応: {name}")

        cmd = self._detect_pkg_manager()
        if cmd is None:
            raise RuntimeError(
                "対応するパッケージマネージャが見つかりませんでした。\n"
                "ターミナルで手動インストールしてください "
                "(例: sudo apt-get install aria2)。"
            )

        pkexec = shutil.which("pkexec")
        if pkexec is None:
            raise RuntimeError(
                "pkexec が見つかりません。\n"
                "ターミナルで手動インストールしてください "
                "(例: sudo apt-get install aria2)。"
            )

        _run_checked([pkexec, *cmd])
        return self._save_path("aria2c", shutil.which("aria2c"))

    def _detect_pkg_manager(self) -> Optional[List[str]]:
        for cmd in _LINUX_PKG_MANAGERS:
            if shutil.which(cmd[0]):
                return cmd
        return None

    def _install_brew(self, name: str) -> Optional[str]:
        brew = shutil.which("brew")
        if not brew:
            raise RuntimeError(
                "Homebrew (brew) が見つかりません。\n"
                "以下のコマンドをターミナルに貼り付けて Homebrew を"
                "インストールしてください:\n\n"
                '/bin/bash -c "$(curl -fsSL'
                ' https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"\n\n'
                "インストール後、アプリを再起動して再度セットアップを実行してください。"
            )

        package = _BREW_NAMES.get(name)
        if not package:
            raise ValueError(f"Homebrew パッケージが不明です: {name}")

        _run_checked([brew, "install", package])
        return self._save_path(name, shutil.which(name))

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------

    def _save_path(self, name: str, path: Optional[str]) -> Optional[str]:
        # 見つかったパスを設定ファイルへ保存し、そのまま返す。
        if path:
            self._config.set(_CONFIG_KEYS[name], path)
        return path


# ─────────────────────────────────────────────────────────────────────
# モジュールレベルのユーティリティ
# ─────────────────────────────────────────────────────────────────────

def _run_checked(
    cmd: List[str],
    fallback_message: str = "コマンドの実行に失敗しました。",
) -> None:
    # subprocess.run を実行し、終了コードが非 0 なら RuntimeError を投げる。
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or fallback_message)


def _download_file(
    url: str,
    dest: Path,
    progress: Optional[ProgressCallback],
    timeout: int = 120,
) -> None:
    # URL からファイルをダウンロードし、進捗コールバックを呼ぶ。
    dest.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, stream=True, timeout=timeout, allow_redirects=True)
    response.raise_for_status()

    total = int(response.headers.get("content-length", 0))
    downloaded = 0

    with dest.open("wb") as fh:
        for chunk in response.iter_content(chunk_size=65_536):
            if not chunk:
                continue
            fh.write(chunk)
            downloaded += len(chunk)
            if progress and total:
                progress(int(downloaded / total * 100))

    _emit(progress, 100)


def _extract_ffmpeg(archive_path: Path, dest: Path, target_name: str) -> None:
    # アーカイブから ffmpeg 実行ファイルを 1 本だけ取り出して dest に書き出す。
    # zip / tar.xz の両方に対応 (zip 判定で分岐)。
    dest.parent.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(archive_path):
        _extract_member_from_zip(archive_path, dest, target_name)
    else:
        _extract_member_from_tar(archive_path, dest, target_name)


def _extract_member_from_zip(archive_path: Path, dest: Path, target_name: str) -> None:
    with zipfile.ZipFile(archive_path) as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            if Path(member.filename).name.lower() == target_name.lower():
                with zf.open(member) as src, dest.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                return
    raise RuntimeError(
        f"{target_name} が zip アーカイブ内に見つかりませんでした"
    )


def _extract_member_from_tar(archive_path: Path, dest: Path, target_name: str) -> None:
    with tarfile.open(archive_path, "r:*") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            if Path(member.name).name == target_name:
                src = tar.extractfile(member)
                if src is None:
                    continue
                try:
                    with dest.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
                finally:
                    src.close()
                return
    raise RuntimeError(
        f"{target_name} が tar アーカイブ内に見つかりませんでした"
    )


def _make_executable(path: Path) -> None:
    # ファイルに実行ビットを立てる (chmod +x)。
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _emit(callback: Optional[ProgressCallback], value: int) -> None:
    # コールバックが None でなければ進捗値を発火する。
    if callback is not None:
        callback(value)


def _scale_progress(
    callback: Optional[ProgressCallback],
    lo: int,
    hi: int,
) -> Optional[ProgressCallback]:
    # 0–100 の進捗を [lo, hi] 範囲にマッピングするラッパを返す。
    if callback is None:
        return None
    return lambda pct: callback(lo + int(pct * (hi - lo) / 100))
