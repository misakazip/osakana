# yt-dlp / ffmpeg / deno / aria2c バイナリの検出とインストールを行う。
#
# 設計方針:
#
# * yt-dlp / ffmpeg / deno は全プラットフォームで GitHub Releases 等から
#   直接ダウンロードし、~/.osakana/bin/ 配下に保存する。アプリは常に
#   このローカルコピーを呼び出す。
# * aria2c は Windows のみ GitHub Releases からダウンロードする。
#   Linux/macOS には公式の単体バイナリが無いため自動インストールは行わず、
#   ユーザがシステムパッケージマネージャ (apt / dnf / pacman / brew 等)
#   経由で別途インストールする想定。find() はシステム PATH を検索する。
from __future__ import annotations

import shutil
import stat
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

# アプリの動作に必須のバイナリ (起動時にウィザードで補充される)
REQUIRED: List[str] = ["yt-dlp", "ffmpeg"]

# ローカルインストール先 (~/.osakana/bin)
INSTALL_DIR: Path = Path.home() / ".osakana" / "bin"

# BtbN FFmpeg ビルドの共通 URL プレフィックス
_BTBN_BASE = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"

# yt-dlp 公式リリースのベース URL
_YTDLP_BASE = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/"

# deno 公式リリースのベース URL
_DENO_BASE = "https://github.com/denoland/deno/releases/latest/download/"

# aria2 公式リリース (GitHub Releases にアップロード済みの固定バージョンを使用する。
# aria2 はリリース頻度が低いので、URL を壊さないために明示的に固定する)
_ARIA2_VERSION = "1.37.0"
_ARIA2_BASE = (
    f"https://github.com/aria2/aria2/releases/download/release-{_ARIA2_VERSION}/"
)

# 設定ファイルのキー
_CONFIG_KEYS: Dict[str, str] = {
    "yt-dlp": "YtdlpPath",
    "ffmpeg": "FfmpegPath",
    "deno":   "DenoPath",
    "aria2c": "Aria2cPath",
}

# 進捗コールバック (0–100)
ProgressCallback = Callable[[int], None]


# ─────────────────────────────────────────────────────────────────────
# 管理ポリシー
# ─────────────────────────────────────────────────────────────────────

def _is_managed(name: str, platform: PlatformInfo) -> bool:
    # このバイナリを ~/.osakana/bin/ でローカル管理するかを返す。
    # 管理対象は find() / install() が URL ダウンロード経路を使い、
    # それ以外はシステム PATH + パッケージマネージャ経路を使う。
    if name in ("yt-dlp", "ffmpeg", "deno"):
        return True
    if name == "aria2c":
        # aria2 は Windows にしか公式バイナリが無い
        return platform.is_windows
    return False


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


def _deno_url(platform: PlatformInfo) -> str:
    # deno 公式は全プラットフォームで zip アーカイブを提供する
    target = _deno_target(platform)
    return _DENO_BASE + f"deno-{target}.zip"


def _deno_target(platform: PlatformInfo) -> str:
    if platform.is_windows:
        # 公式の Windows ビルドは x86_64 のみ
        return "x86_64-pc-windows-msvc"
    if platform.is_macos:
        return "aarch64-apple-darwin" if platform.is_arm64 else "x86_64-apple-darwin"
    if platform.is_linux:
        return "aarch64-unknown-linux-gnu" if platform.is_arm64 else "x86_64-unknown-linux-gnu"
    raise RuntimeError(
        f"deno の配布物はこの OS には用意されていません: {platform.display_name}"
    )


def _aria2c_url(platform: PlatformInfo) -> str:
    # aria2c は Windows ビルドのみ URL ダウンロードに対応する
    if not platform.is_windows:
        raise RuntimeError(
            f"aria2c の URL ダウンロードは Windows のみ対応しています "
            f"(現在の OS: {platform.display_name})"
        )
    if platform.is_arm64:
        # 公式の aria2 Windows ビルドに arm64 は無い
        raise RuntimeError("aria2c の公式 Windows ARM64 ビルドは提供されていません")
    return _ARIA2_BASE + f"aria2-{_ARIA2_VERSION}-win-64bit-build1.zip"


def _local_filename(name: str, platform: PlatformInfo) -> str:
    # Windows のみ .exe 拡張子を付ける
    return f"{name}.exe" if platform.is_windows else name


# ─────────────────────────────────────────────────────────────────────
# BinaryManager
# ─────────────────────────────────────────────────────────────────────

class BinaryManager:
    # yt-dlp / ffmpeg / deno / aria2c の検出とインストールを担うファサード。

    def __init__(self, config: Config, platform: PlatformInfo) -> None:
        self._config = config
        self._platform = platform
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 検出
    # ------------------------------------------------------------------

    def find(self, name: str) -> Optional[str]:
        # 管理対象は INSTALL_DIR のローカルコピーのみを参照する。
        # システム PATH 上の別バージョンが混入しないようにするため。
        if _is_managed(name, self._platform):
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
        # aria2c (Linux/macOS) などはシステム PATH を尊重する
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
        # 管理対象外のバイナリ (Linux/macOS の aria2c など) は自動インストール
        # を行わず、ユーザにシステムパッケージマネージャでの導入を促す。
        if _is_managed(name, self._platform):
            return self._install_managed(name, progress)
        raise RuntimeError(
            f"{name} の自動インストールは {self._platform.display_name} では"
            f"対応していません。システムのパッケージマネージャ (apt / dnf / "
            f"pacman / brew など) でインストールしてください。"
        )

    # ------------------------------------------------------------------
    # 管理バイナリの URL ダウンロード
    # ------------------------------------------------------------------

    def _install_managed(
        self, name: str, progress: Optional[ProgressCallback]
    ) -> str:
        if name == "yt-dlp":
            return self._install_single_binary(name, _ytdlp_url(self._platform), progress)
        if name == "ffmpeg":
            return self._install_archived_binary(
                "ffmpeg", _ffmpeg_url(self._platform), progress,
                archive_suffix=".zip" if (self._platform.is_windows or self._platform.is_macos) else ".tar.xz",
            )
        if name == "deno":
            return self._install_archived_binary(
                "deno", _deno_url(self._platform), progress,
                archive_suffix=".zip",
            )
        if name == "aria2c":
            return self._install_archived_binary(
                "aria2c", _aria2c_url(self._platform), progress,
                archive_suffix=".zip",
            )
        raise ValueError(f"未知の管理バイナリ: {name}")

    def _install_single_binary(
        self, name: str, url: str, progress: Optional[ProgressCallback]
    ) -> str:
        # アーカイブではなく単体実行ファイルを直接 INSTALL_DIR に保存する。
        dest = INSTALL_DIR / _local_filename(name, self._platform)
        _download_file(url, dest, progress)
        if not self._platform.is_windows:
            _make_executable(dest)

        self._config.set(_CONFIG_KEYS[name], str(dest))
        return str(dest)

    def _install_archived_binary(
        self,
        name: str,
        url: str,
        progress: Optional[ProgressCallback],
        archive_suffix: str,
    ) -> str:
        # アーカイブ (.zip / .tar.xz) をダウンロードし、
        # 目的の実行ファイルを 1 本だけ INSTALL_DIR に展開する。
        dest = INSTALL_DIR / _local_filename(name, self._platform)
        target_member = _local_filename(name, self._platform)

        with tempfile.NamedTemporaryFile(suffix=archive_suffix, delete=False) as tmp:
            archive_path = Path(tmp.name)

        try:
            # 0–80%: ダウンロード
            _download_file(url, archive_path, _scale_progress(progress, 0, 80))
            _emit(progress, 85)

            # 85–100%: 展開
            _extract_binary_from_archive(archive_path, dest, target_member)
            if not self._platform.is_windows:
                _make_executable(dest)
            _emit(progress, 100)
        finally:
            archive_path.unlink(missing_ok=True)

        self._config.set(_CONFIG_KEYS[name], str(dest))
        return str(dest)

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


def _extract_binary_from_archive(
    archive_path: Path, dest: Path, target_name: str
) -> None:
    # アーカイブから特定の実行ファイルを 1 本だけ取り出して dest に書き出す。
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
