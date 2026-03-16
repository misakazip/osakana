"""ダウンロードエンジン: yt-dlp をサブプロセスとしてラップする。

各 DownloadTask は専用の DownloadWorker（QThread）で実行される。
DownloadManager はタスクをキューに入れ、MaxParallelDownloads を遵守する。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# Windows でサブプロセスのコンソールウィンドウを非表示にするフラグ
_POPEN_FLAGS: dict = (
    {"creationflags": 0x08000000} if sys.platform == "win32" else {}
)

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from .config import Config

# ------------------------------------------------------------------
# フォーマット / 画質プリセット
# ------------------------------------------------------------------

VIDEO_QUALITY_MAP: Dict[str, str] = {
    "Best": "bestvideo+bestaudio/best",
    "4K (2160p)": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
    "Full HD (1080p)": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "HD (720p)": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "SD (480p)": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
}

VIDEO_QUALITIES = list(VIDEO_QUALITY_MAP)
AUDIO_FORMATS = ["best", "mp3", "m4a", "opus", "flac", "wav"]
CONTAINERS = ["mp4", "mkv", "webm", "avi"]

# ------------------------------------------------------------------
# 進捗のパース
# ------------------------------------------------------------------

_PROGRESS_RE = re.compile(
    r"\[download\]\s+([\d.]+)%\s+of\s+[\d.~]+\S+"
    r"(?:\s+at\s+([\d.]+\S+)\s+ETA\s+(\S+))?"
)


# ------------------------------------------------------------------
# データモデル
# ------------------------------------------------------------------

@dataclass
class DownloadTask:
    url: str
    output_dir: str
    quality: str = "Best"
    audio_only: bool = False
    audio_format: str = "mp3"
    container: str = "mp4"
    embed_subtitles: bool = False
    playlist: bool = False
    convert_h265: bool = False
    avoid_bot_detection: bool = False
    members_only: bool = False  # メンバー限定動画のみダウンロードする
    trim_start: str = ""        # "HH:MM:SS" または秒数、空 = トリムなし
    trim_end: str = ""          # "HH:MM:SS" または秒数、空 = 動画の末尾まで
    filename_template: str = "%(title)s [%(id)s].%(ext)s"  # yt-dlp の -o テンプレート
    # 実行時の状態
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "queued"   # queued | downloading | processing | done | failed | cancelled
    progress: float = 0.0
    speed: str = ""
    eta: str = ""
    title: str = ""
    error: str = ""


# ------------------------------------------------------------------
# ワーカースレッド
# ------------------------------------------------------------------

class DownloadWorker(QThread):
    progress_updated = pyqtSignal(str, float, str, str)   # id, %, 速度, ETA
    status_changed   = pyqtSignal(str, str)                # id, ステータス
    title_fetched    = pyqtSignal(str, str)                # id, タイトル
    download_done    = pyqtSignal(str, bool, str)          # id, 成否, エラー
    raw_output       = pyqtSignal(str, str)                # id, 生の出力行

    def __init__(self, task: DownloadTask, config: Config, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.task = task
        self._config = config
        self._process: Optional[subprocess.Popen[str]] = None
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # QThread エントリーポイント
    # ------------------------------------------------------------------

    def run(self) -> None:
        self.status_changed.emit(self.task.id, "downloading")

        # タイトルを事前取得する（ベストエフォート、失敗しても非致命的）
        title = self._fetch_title()
        if title:
            self.title_fetched.emit(self.task.id, title)

        cmd = self._build_command()
        env = self._build_env()

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                **_POPEN_FLAGS,
            )
            assert self._process.stdout is not None
            for line in iter(self._process.stdout.readline, ""):
                if self._cancelled:
                    break
                self.raw_output.emit(self.task.id, line.rstrip())
                self._parse_line(line)

            self._process.wait()

            if self._cancelled:
                self.status_changed.emit(self.task.id, "cancelled")
                self.download_done.emit(self.task.id, False, "cancelled")
            elif self._process.returncode == 0:
                self.progress_updated.emit(self.task.id, 100.0, "", "")
                self.status_changed.emit(self.task.id, "done")
                self.download_done.emit(self.task.id, True, "")
            else:
                self.status_changed.emit(self.task.id, "failed")
                self.download_done.emit(
                    self.task.id, False, f"終了コード {self._process.returncode}"
                )
        except Exception as exc:
            self.status_changed.emit(self.task.id, "failed")
            self.download_done.emit(self.task.id, False, str(exc))

    # ------------------------------------------------------------------
    # コマンド構築
    # ------------------------------------------------------------------

    def _build_command(self) -> List[str]:
        task = self.task
        ytdlp = self._config.get("YtdlpPath", "yt-dlp")
        cmd = [ytdlp, "--newline", "--progress", "--no-colors"]

        self._add_format_args(cmd, task)
        self._add_subtitle_args(cmd, task)

        if not task.playlist:
            cmd += ["--no-playlist"]

        tpl = task.filename_template or "%(title)s [%(id)s].%(ext)s"
        cmd += ["-o", str(Path(task.output_dir) / tpl)]

        if task.trim_start or task.trim_end:
            start = task.trim_start or "0"
            end   = task.trim_end   or "inf"
            cmd += ["--download-sections", f"*{start}-{end}", "--force-keyframes-at-cuts"]

        if task.avoid_bot_detection:
            cmd += ["--rate-limit", "5M", "--min-sleep-interval", "15", "--max-sleep-interval", "45"]

        if task.members_only:
            cmd += ["--match-filter", "availability=subscriber_only"]

        self._add_postprocess_args(cmd, task)
        self._add_download_ctrl_args(cmd)
        self._add_network_args(cmd)

        extra_args = self._config.get("ExtraArgs", "").strip()
        if extra_args:
            import shlex
            cmd += shlex.split(extra_args)

        cmd.append(task.url)
        return cmd

    def _add_format_args(self, cmd: List[str], task: "DownloadTask") -> None:
        if task.audio_only:
            # Windows は Opus を再生できないため M4A (AAC) に自動変換する
            audio_fmt = task.audio_format if task.audio_format != "opus" else "m4a"
            cmd += ["-x", "--audio-format", audio_fmt, "--audio-quality", "0"]
        else:
            fmt = VIDEO_QUALITY_MAP.get(task.quality, "bestvideo+bestaudio/best")
            cmd += ["-f", fmt, "--merge-output-format", task.container]
            if task.convert_h265:
                cmd += ["--postprocessor-args", "ffmpeg:-c:v libx265 -crf 28 -preset medium -c:a copy"]

    def _add_subtitle_args(self, cmd: List[str], task: "DownloadTask") -> None:
        if not task.embed_subtitles or task.audio_only:
            return
        sub_langs  = self._config.get("SubLangs", "ja,en") or "all,-live_chat"
        sub_format = self._config.get("SubFormat", "srt")
        cmd += ["--embed-subs", "--sub-langs", sub_langs, "--sub-format", sub_format]
        # "--convert-subs" は ass/lrc/srt/vtt のみ有効。"best" には使えない
        if sub_format != "best":
            cmd += ["--convert-subs", sub_format]
        if self._config.get("AutoSubs"):
            cmd += ["--write-auto-subs"]

    def _add_postprocess_args(self, cmd: List[str], task: "DownloadTask") -> None:
        if self._config.get("EmbedThumbnail"):
            cmd += ["--embed-thumbnail"]
        if self._config.get("EmbedMetadata"):
            cmd += ["--embed-metadata"]
        # SponsorBlock は映像の章マーカーと ffmpeg が必要なため音声のみ時はスキップ
        sponsorblock = self._config.get("SponsorBlock", "off")
        if sponsorblock and sponsorblock != "off" and not task.audio_only:
            cmd += ["--sponsorblock-remove", sponsorblock]

    def _add_download_ctrl_args(self, cmd: List[str]) -> None:
        speed_limit = self._config.get("SpeedLimit", "").strip()
        if speed_limit:
            cmd += ["--limit-rate", speed_limit]
        cmd += ["--retries", str(self._config.get("Retries", 10))]
        archive = self._config.get("DownloadArchive", "").strip()
        if archive:
            cmd += ["--download-archive", archive]

    def _add_network_args(self, cmd: List[str]) -> None:
        proxy = self._config.get("Proxy", "").strip()
        if proxy:
            cmd += ["--proxy", proxy]
        cookies_browser = self._config.get("CookiesBrowser", "").strip()
        if cookies_browser:
            cmd += ["--cookies-from-browser", cookies_browser]
        if self._config.get("IsAria2cEnabled"):
            connections = self._config.get("Aria2cConnections", 16)
            cmd += ["--downloader", "aria2c", "--downloader-args",
                    f"aria2c:-x {connections} -s {connections} -k 1M"]

    def _build_env(self) -> dict:
        env = os.environ.copy()
        extra_paths: List[str] = []

        ffmpeg = self._config.get("FfmpegPath", "")
        if ffmpeg:
            extra_paths.append(str(Path(ffmpeg).parent))

        aria2c = self._config.get("Aria2cPath", "")
        if aria2c and self._config.get("IsAria2cEnabled"):
            extra_paths.append(str(Path(aria2c).parent))

        if extra_paths:
            env["PATH"] = os.pathsep.join(extra_paths) + os.pathsep + env.get("PATH", "")
        return env

    # ------------------------------------------------------------------
    # 出力のパース
    # ------------------------------------------------------------------

    def _parse_line(self, line: str) -> None:
        m = _PROGRESS_RE.search(line)
        if m:
            pct = float(m.group(1))
            speed = m.group(2) or ""
            eta = m.group(3) or ""
            self.progress_updated.emit(self.task.id, pct, speed, eta)
            return

        if any(tag in line for tag in ("[Merger]", "[ExtractAudio]", "[ffmpeg]")):
            self.status_changed.emit(self.task.id, "processing")

    def _fetch_title(self) -> str:
        try:
            ytdlp = self._config.get("YtdlpPath", "yt-dlp")
            result = subprocess.run(
                [ytdlp, "--print", "title", "--no-playlist", self.task.url],
                capture_output=True,
                text=True,
                timeout=30,
                env=self._build_env(),
                **_POPEN_FLAGS,
            )
            return result.stdout.strip().splitlines()[0] if result.returncode == 0 else ""
        except Exception:
            return ""


# ------------------------------------------------------------------
# ダウンロードマネージャ（ワーカーを管理）
# ------------------------------------------------------------------

class DownloadManager(QObject):
    """ダウンロードキューと並列ワーカースレッドを管理する。"""

    task_added       = pyqtSignal(object)          # DownloadTask
    progress_updated = pyqtSignal(str, float, str, str)
    status_changed   = pyqtSignal(str, str)
    title_fetched    = pyqtSignal(str, str)
    download_done    = pyqtSignal(str, bool, str)
    raw_output       = pyqtSignal(str, str)         # id, 生の出力行
    queue_stats      = pyqtSignal(int, int)         # アクティブ数, キュー数

    def __init__(self, config: Config, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._config = config
        self._pending: List[DownloadTask] = []
        self._active: Dict[str, DownloadWorker] = {}

    # ------------------------------------------------------------------
    # 公開API
    # ------------------------------------------------------------------

    def add(self, task: DownloadTask) -> None:
        self._pending.append(task)
        self.task_added.emit(task)
        self._dispatch()

    def cancel(self, task_id: str) -> None:
        if task_id in self._active:
            self._active[task_id].cancel()
        else:
            self._pending = [t for t in self._pending if t.id != task_id]
            self.status_changed.emit(task_id, "cancelled")
            self._emit_stats()

    # ------------------------------------------------------------------
    # 内部スケジューリング
    # ------------------------------------------------------------------

    def _dispatch(self) -> None:
        max_parallel = self._config.get("MaxParallelDownloads", 2)
        while len(self._active) < max_parallel and self._pending:
            task = self._pending.pop(0)
            self._start_worker(task)
        self._emit_stats()

    def _start_worker(self, task: DownloadTask) -> None:
        worker = DownloadWorker(task, self._config, parent=self)
        worker.progress_updated.connect(self.progress_updated)
        worker.status_changed.connect(self.status_changed)
        worker.title_fetched.connect(self.title_fetched)
        worker.raw_output.connect(self.raw_output)
        worker.download_done.connect(self._on_done)
        self._active[task.id] = worker
        worker.start()

    def _on_done(self, task_id: str, success: bool, error: str) -> None:
        self._active.pop(task_id, None)
        self.download_done.emit(task_id, success, error)
        self._dispatch()

    def _emit_stats(self) -> None:
        self.queue_stats.emit(len(self._active), len(self._pending))
