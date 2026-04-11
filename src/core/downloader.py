# ダウンロードエンジン: yt-dlp をサブプロセスとしてラップする。
#
# 各 DownloadTask は専用の DownloadWorker (QThread) で実行され、
# DownloadManager がキュー管理と並列度 (MaxParallelDownloads) の制御を担う。
from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, QThread, Signal

from .config import Config

# ─────────────────────────────────────────────────────────────────────
# プラットフォーム依存の Popen フラグ
# ─────────────────────────────────────────────────────────────────────

# Windows ではサブプロセスのコンソールウィンドウを抑制する。
# 他プラットフォームでは空辞書を渡せばよい (no-op)。
_POPEN_FLAGS: Dict[str, int] = (
    {"creationflags": 0x08000000} if sys.platform == "win32" else {}
)

# ─────────────────────────────────────────────────────────────────────
# フォーマット / 画質プリセット
# ─────────────────────────────────────────────────────────────────────

VIDEO_QUALITY_MAP: Dict[str, str] = {
    "Best":             "bestvideo+bestaudio/best",
    "4K (2160p)":       "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
    "Full HD (1080p)":  "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "HD (720p)":        "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "SD (480p)":        "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p":             "bestvideo[height<=360]+bestaudio/best[height<=360]",
}
VIDEO_QUALITIES: List[str] = list(VIDEO_QUALITY_MAP)

AUDIO_FORMATS: List[str] = ["best", "mp3", "m4a", "opus", "flac", "wav"]
CONTAINERS:    List[str] = ["mp4", "mkv", "webm", "avi"]

DEFAULT_FILENAME_TEMPLATE = "%(title)s [%(id)s].%(ext)s"

# ハードウェアエンコーダ別の H.265 ffmpeg オプション
_HW_ENCODER: Dict[str, str] = {
    "nvidia": "hevc_nvenc -rc vbr -cq 28 -preset p4",
    "amd":    "hevc_amf -quality balanced -qp_i 28 -qp_p 28",
    "intel":  "hevc_qsv -global_quality 28 -preset medium",
}
_SW_ENCODER = "libx265 -crf 28 -preset medium"

# ─────────────────────────────────────────────────────────────────────
# タスクのステータス定数
# ─────────────────────────────────────────────────────────────────────

class Status:
    # ダウンロードタスクの状態を表す文字列定数。

    QUEUED      = "queued"
    DOWNLOADING = "downloading"
    PROCESSING  = "processing"
    DONE        = "done"
    FAILED      = "failed"
    CANCELLED   = "cancelled"

    # 終了状態 (それ以上遷移しない) の集合
    TERMINAL = frozenset({DONE, FAILED, CANCELLED})


# ─────────────────────────────────────────────────────────────────────
# 進捗のパース
# ─────────────────────────────────────────────────────────────────────

# 例: [download]  42.5% of 100.00MiB at 1.20MiB/s ETA 00:30
_PROGRESS_RE = re.compile(
    r"\[download\]\s+([\d.]+)%\s+of\s+[\d.~]+\S+"
    r"(?:\s+at\s+([\d.]+\S+)\s+ETA\s+(\S+))?"
)

# 後処理を示す yt-dlp のタグ
_POSTPROCESS_TAGS = ("[Merger]", "[ExtractAudio]", "[ffmpeg]")


# ─────────────────────────────────────────────────────────────────────
# データモデル
# ─────────────────────────────────────────────────────────────────────

@dataclass
class DownloadTask:
    # ダウンロード 1 件分の設定と実行時状態。

    # ── ユーザ指定 ────────────────────────────────────────────
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
    members_only: bool = False                # メンバー限定動画のみダウンロードする
    trim_start: str = ""                      # "HH:MM:SS" / 秒数 / 空 = 先頭から
    trim_end: str = ""                        # "HH:MM:SS" / 秒数 / 空 = 末尾まで
    filename_template: str = DEFAULT_FILENAME_TEMPLATE  # yt-dlp の -o テンプレート

    # ── 実行時の状態 ─────────────────────────────────────────
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = Status.QUEUED
    progress: float = 0.0
    speed: str = ""
    eta: str = ""
    title: str = ""
    error: str = ""


# ─────────────────────────────────────────────────────────────────────
# ワーカースレッド
# ─────────────────────────────────────────────────────────────────────

class DownloadWorker(QThread):
    # 単一の DownloadTask を yt-dlp サブプロセスとして実行する。

    # シグナル定義
    progress_updated = Signal(str, float, str, str)  # id, %, 速度, ETA
    status_changed   = Signal(str, str)              # id, ステータス
    title_fetched    = Signal(str, str)              # id, タイトル
    download_done    = Signal(str, bool, str)        # id, 成否, エラー
    raw_output       = Signal(str, str)              # id, 生の出力行

    def __init__(
        self,
        task: DownloadTask,
        config: Config,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.task = task
        self._config = config
        self._process: Optional[subprocess.Popen[str]] = None
        self._cancelled = False

    # ------------------------------------------------------------------
    # 公開API
    # ------------------------------------------------------------------

    def cancel(self) -> None:
        # 進行中のダウンロードを中止する。
        self._cancelled = True
        if self._process is not None:
            try:
                self._process.terminate()
            except Exception:
                pass  # 既に終了している場合は無視

    # ------------------------------------------------------------------
    # QThread エントリーポイント
    # ------------------------------------------------------------------

    def run(self) -> None:
        self.status_changed.emit(self.task.id, Status.DOWNLOADING)

        # タイトルの事前取得 (ベストエフォート、失敗しても続行)
        title = self._fetch_title()
        if title:
            self.title_fetched.emit(self.task.id, title)

        try:
            self._run_ytdlp()
        except Exception as exc:
            self.status_changed.emit(self.task.id, Status.FAILED)
            self.download_done.emit(self.task.id, False, str(exc))

    def _run_ytdlp(self) -> None:
        # yt-dlp を起動し、出力をパースしてシグナルを発火する。
        cmd = self._build_command()
        env = self._build_env()

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
        self._emit_final_status()

    def _emit_final_status(self) -> None:
        # 終了コードに応じて最終ステータスを発火する。
        assert self._process is not None
        if self._cancelled:
            self.status_changed.emit(self.task.id, Status.CANCELLED)
            self.download_done.emit(self.task.id, False, "cancelled")
        elif self._process.returncode == 0:
            self.progress_updated.emit(self.task.id, 100.0, "", "")
            self.status_changed.emit(self.task.id, Status.DONE)
            self.download_done.emit(self.task.id, True, "")
        else:
            self.status_changed.emit(self.task.id, Status.FAILED)
            self.download_done.emit(
                self.task.id, False, f"終了コード {self._process.returncode}"
            )

    # ------------------------------------------------------------------
    # コマンド構築
    # ------------------------------------------------------------------

    def _build_command(self) -> List[str]:
        task = self.task
        ytdlp = self._config.get("YtdlpPath", "yt-dlp")
        cmd: List[str] = [ytdlp, "--newline", "--progress", "--no-colors"]

        # ffmpeg は ~/.osakana/bin にあるローカルコピーを yt-dlp に明示する。
        # PATH 経由よりも --ffmpeg-location が優先されるため確実。
        ffmpeg = self._config.get("FfmpegPath", "")
        if ffmpeg:
            cmd += ["--ffmpeg-location", ffmpeg]

        self._add_format_args(cmd, task)
        self._add_subtitle_args(cmd, task)

        if not task.playlist:
            cmd += ["--no-playlist"]

        # 出力テンプレート
        template = task.filename_template or DEFAULT_FILENAME_TEMPLATE
        cmd += ["-o", str(Path(task.output_dir) / template)]

        # トリミング (--download-sections)
        if task.trim_start or task.trim_end:
            start = task.trim_start or "0"
            end   = task.trim_end   or "inf"
            cmd += [
                "--download-sections", f"*{start}-{end}",
                "--force-keyframes-at-cuts",
            ]

        # bot 検知回避: レート制限とランダムスリープを設定
        if task.avoid_bot_detection:
            cmd += [
                "--rate-limit", "5M",
                "--min-sleep-interval", "15",
                "--max-sleep-interval", "45",
            ]

        # メンバーシップ限定動画のフィルタ
        if task.members_only:
            cmd += ["--match-filter", "availability=subscriber_only"]

        self._add_postprocess_args(cmd, task)
        self._add_download_ctrl_args(cmd)
        self._add_network_args(cmd)

        # ユーザ指定の追加引数 (シェル風にパース)
        extra_args = self._config.get("ExtraArgs", "").strip()
        if extra_args:
            cmd += shlex.split(extra_args)

        cmd.append(task.url)
        return cmd

    def _add_format_args(self, cmd: List[str], task: DownloadTask) -> None:
        # 音声/動画フォーマット関連の引数を追加する。
        if task.audio_only:
            # Windows は Opus を再生できないため M4A (AAC) に自動変換する
            audio_fmt = "m4a" if task.audio_format == "opus" else task.audio_format
            cmd += ["-x", "--audio-format", audio_fmt, "--audio-quality", "0"]
            return

        fmt = VIDEO_QUALITY_MAP.get(task.quality, VIDEO_QUALITY_MAP["Best"])
        cmd += ["-f", fmt, "--merge-output-format", task.container]

        if task.convert_h265:
            hw_accel = self._config.get("HwAccel", "none")
            vcodec = _HW_ENCODER.get(hw_accel, _SW_ENCODER)
            cmd += [
                "--postprocessor-args",
                f"Merger+ffmpeg:-c:v {vcodec} -c:a aac -b:a 192k",
            ]
        else:
            cmd += [
                "--postprocessor-args",
                "Merger+ffmpeg:-c:v copy -c:a aac -b:a 192k",
            ]

    def _add_subtitle_args(self, cmd: List[str], task: DownloadTask) -> None:
        if not task.embed_subtitles or task.audio_only:
            return
        sub_langs  = self._config.get("SubLangs", "ja,en") or "all,-live_chat"
        sub_format = self._config.get("SubFormat", "srt")
        cmd += ["--embed-subs", "--sub-langs", sub_langs, "--sub-format", sub_format]
        # --convert-subs は ass/lrc/srt/vtt のみ有効、"best" には使えない
        if sub_format != "best":
            cmd += ["--convert-subs", sub_format]
        if self._config.get("AutoSubs"):
            cmd += ["--write-auto-subs"]

    def _add_postprocess_args(self, cmd: List[str], task: DownloadTask) -> None:
        if self._config.get("EmbedThumbnail"):
            cmd += ["--embed-thumbnail", "--convert-thumbnails", "jpg"]
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
            cmd += [
                "--downloader", "aria2c",
                "--downloader-args", f"aria2c:-x {connections} -s {connections} -k 1M",
            ]

    def _build_env(self) -> Dict[str, str]:
        # ffmpeg / deno / aria2c のディレクトリを PATH 先頭に追加した環境変数を返す。
        # ffmpeg は --ffmpeg-location でも渡しているが、yt-dlp 内部のフォールバックや
        # ffprobe 検出のために PATH にも乗せておく。
        # deno は一部 yt-dlp エクストラクタが JS 実行に使うため PATH 経由で検出される。
        env = os.environ.copy()
        extra_paths: List[str] = []

        for key in ("FfmpegPath", "DenoPath"):
            path = self._config.get(key, "")
            if path:
                extra_paths.append(str(Path(path).parent))

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
        # yt-dlp の 1 行を解析し、進捗 / ステータスを発火する。
        match = _PROGRESS_RE.search(line)
        if match:
            pct   = float(match.group(1))
            speed = match.group(2) or ""
            eta   = match.group(3) or ""
            self.progress_updated.emit(self.task.id, pct, speed, eta)
            return

        if any(tag in line for tag in _POSTPROCESS_TAGS):
            self.status_changed.emit(self.task.id, Status.PROCESSING)

    def _fetch_title(self) -> str:
        # yt-dlp --print title でタイトルを取得する (失敗時は空文字)。
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
            if result.returncode != 0:
                return ""
            lines = result.stdout.strip().splitlines()
            return lines[0] if lines else ""
        except Exception:
            return ""


# ─────────────────────────────────────────────────────────────────────
# ダウンロードマネージャ
# ─────────────────────────────────────────────────────────────────────

class DownloadManager(QObject):
    # ダウンロードキューと並列ワーカースレッドを管理する。

    # シグナル定義
    task_added       = Signal(object)                 # DownloadTask
    progress_updated = Signal(str, float, str, str)
    status_changed   = Signal(str, str)
    title_fetched    = Signal(str, str)
    download_done    = Signal(str, bool, str)
    raw_output       = Signal(str, str)               # id, 生の出力行
    queue_stats      = Signal(int, int)               # アクティブ数, キュー数

    def __init__(self, config: Config, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._config = config
        self._pending: List[DownloadTask] = []
        self._active: Dict[str, DownloadWorker] = {}

    # ------------------------------------------------------------------
    # 公開API
    # ------------------------------------------------------------------

    def add(self, task: DownloadTask) -> None:
        # タスクをキューへ追加し、可能なら即座に実行する。
        self._pending.append(task)
        self.task_added.emit(task)
        self._dispatch()

    def cancel(self, task_id: str) -> None:
        # 指定タスクをキャンセル (実行中はプロセス停止、待機中は破棄)。
        if task_id in self._active:
            self._active[task_id].cancel()
            return
        self._pending = [t for t in self._pending if t.id != task_id]
        self.status_changed.emit(task_id, Status.CANCELLED)
        self._emit_stats()

    # ------------------------------------------------------------------
    # 内部スケジューリング
    # ------------------------------------------------------------------

    def _dispatch(self) -> None:
        # 空きスロットがあれば待機中タスクを順次起動する。
        max_parallel = self._config.get("MaxParallelDownloads", 2)
        while len(self._active) < max_parallel and self._pending:
            self._start_worker(self._pending.pop(0))
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
