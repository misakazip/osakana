# TrimWidget — 動画プレビュープレーヤー付きの切り抜き範囲セレクタ。
#
# レイアウト:
#
#     [開始: HH:MM:SS] [←現在位置]   [終了: HH:MM:SS] [←現在位置]
#     ┌──────────────── video ─────────────────────────────────┐
#     │                                                         │
#     └─────────────────────────────────────────────────────────┘
#     ──────────────●──────────────  シークバー
#     [▶]  00:01:23 / 00:10:00      [プレビューを読み込む]  ステータス
#
# GroupBox はチェック可能で、チェックを外すと内容が非表示になる。
from __future__ import annotations

import re
import subprocess
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

# ─────────────────────────────────────────────────────────────────────
# Qt Multimedia (オプション依存)
# ─────────────────────────────────────────────────────────────────────

if TYPE_CHECKING:
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PyQt6.QtMultimediaWidgets import QVideoWidget

try:
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer  # noqa: F811
    from PyQt6.QtMultimediaWidgets import QVideoWidget  # noqa: F811
    _MULTIMEDIA_OK = True
except ImportError:
    _MULTIMEDIA_OK = False


# ─────────────────────────────────────────────────────────────────────
# 時刻フォーマットヘルパー
# ─────────────────────────────────────────────────────────────────────

_TIME_RE = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2})$")

# URL 入力から実際にプレビューを読み込むまでの遅延 (ミリ秒)
_URL_DEBOUNCE_MS = 1500


def _parse_seconds(text: str) -> Optional[float]:
    # "HH:MM:SS" / "MM:SS" / 秒数の文字列を float に変換する。
    stripped = text.strip()
    if not stripped:
        return None

    match = _TIME_RE.match(stripped)
    if match:
        hours   = int(match.group(1) or 0)
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        return hours * 3600 + minutes * 60 + seconds

    try:
        return float(stripped)
    except ValueError:
        return None


def _fmt(seconds: float) -> str:
    # 秒数を "HH:MM:SS" (1 時間未満なら "MM:SS") に変換する。
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


# ─────────────────────────────────────────────────────────────────────
# バックグラウンドワーカー: yt-dlp -g でストリーム URL を取得
# ─────────────────────────────────────────────────────────────────────

class _StreamUrlWorker(QThread):
    # yt-dlp -g <url> を実行してストリーム URL を 1 本取得する。

    url_ready = pyqtSignal(str)
    failed    = pyqtSignal(str)

    def __init__(self, url: str, ytdlp_path: str) -> None:
        super().__init__()
        self._url = url
        self._ytdlp_path = ytdlp_path

    def run(self) -> None:
        from core.downloader import _POPEN_FLAGS
        try:
            result = subprocess.run(
                [self._ytdlp_path, "-g", "--no-playlist", self._url],
                capture_output=True,
                text=True,
                timeout=30,
                **_POPEN_FLAGS,
            )
            if result.returncode == 0:
                first_url = result.stdout.strip().splitlines()[0]
                self.url_ready.emit(first_url)
            else:
                self.failed.emit(
                    result.stderr.strip() or "ストリーム URL の取得に失敗しました"
                )
        except Exception as exc:
            self.failed.emit(str(exc))


# ─────────────────────────────────────────────────────────────────────
# TrimWidget
# ─────────────────────────────────────────────────────────────────────

class TrimWidget(QGroupBox):
    # 折りたたみ可能な切り抜き範囲セレクタ (動画プレビュー付き)。

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("切り抜き", parent)
        self.setCheckable(True)
        self.setChecked(False)

        self._ytdlp_path: str = "yt-dlp"
        self._current_url: str = ""
        self._worker: Optional[_StreamUrlWorker] = None
        self._slider_dragging = False

        # URL 変更後のプレビュー自動読み込みをデバウンスするタイマー
        self._url_timer = QTimer(self)
        self._url_timer.setSingleShot(True)
        self._url_timer.setInterval(_URL_DEBOUNCE_MS)
        self._url_timer.timeout.connect(self._load_preview)

        self._setup_ui()

        # GroupBox のチェック状態とコンテンツ可視性を連動
        self.toggled.connect(self._content.setVisible)
        self._content.setVisible(False)

        # 開始 / 終了時刻の変更でプレーヤーをシーク
        self._start_edit.textChanged.connect(self._seek_to_text)
        self._end_edit.textChanged.connect(self._seek_to_text)

    # ------------------------------------------------------------------
    # 公開API
    # ------------------------------------------------------------------

    def set_ytdlp_path(self, path: str) -> None:
        self._ytdlp_path = path or "yt-dlp"

    def set_url(self, url: str) -> None:
        # URL 欄の内容が変わったときに呼ばれる。有効ならプレビューを予約する。
        if url == self._current_url:
            return
        self._current_url = url
        if self.isChecked() and url and _MULTIMEDIA_OK:
            self._url_timer.start()

    def trim_start(self) -> str:
        return self._start_edit.text().strip()

    def trim_end(self) -> str:
        return self._end_edit.text().strip()

    def is_trim_enabled(self) -> bool:
        return self.isChecked()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 4, 6, 6)

        self._content = QWidget()
        inner = QVBoxLayout(self._content)
        inner.setSpacing(6)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.addLayout(self._build_time_row())
        inner.addWidget(self._build_player_area())

        outer.addWidget(self._content)

    def _build_time_row(self) -> QHBoxLayout:
        row = QHBoxLayout()

        self._start_edit, self._start_btn = self._build_time_input("開始:", self._set_start_from_player)
        row.addWidget(QLabel("開始:"))
        row.addWidget(self._start_edit)
        row.addWidget(self._start_btn)

        row.addSpacing(16)

        self._end_edit, self._end_btn = self._build_time_input("終了:", self._set_end_from_player)
        row.addWidget(QLabel("終了:"))
        row.addWidget(self._end_edit)
        row.addWidget(self._end_btn)

        row.addStretch()
        return row

    @staticmethod
    def _build_time_input(label: str, slot) -> tuple[QLineEdit, QPushButton]:
        # HH:MM:SS 入力欄と「← 現在位置」ボタンを作る。
        edit = QLineEdit()
        edit.setPlaceholderText("HH:MM:SS")
        edit.setFixedWidth(85)

        button = QPushButton("← 現在位置")
        button.setFixedWidth(88)
        button.setToolTip(f"プレーヤーの現在位置を{label.rstrip(':')}点に設定")
        button.clicked.connect(slot)
        return edit, button

    def _build_player_area(self) -> QWidget:
        frame = QWidget()
        layout = QVBoxLayout(frame)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        if not _MULTIMEDIA_OK:
            layout.addWidget(QLabel(
                "⚠ PyQt6.QtMultimedia が利用できないため"
                "プレビューは無効です。\n"
                "時刻を手動で入力してください。"
            ))
            self._player = None
            return frame

        # 動画出力ウィジェット
        self._video_widget = QVideoWidget()
        self._video_widget.setMinimumHeight(200)
        self._video_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self._video_widget)

        # シークバー
        self._seek_slider = QSlider(Qt.Orientation.Horizontal)
        self._seek_slider.setRange(0, 0)
        self._seek_slider.sliderPressed.connect(self._on_slider_pressed)
        self._seek_slider.sliderReleased.connect(self._on_slider_released)
        self._seek_slider.sliderMoved.connect(self._on_seek_moved)
        layout.addWidget(self._seek_slider)

        # 再生コントロール行
        layout.addLayout(self._build_control_row())

        # メディアプレーヤー本体
        self._player       = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        self._player.setVideoOutput(self._video_widget)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self._on_playback_state_changed)

        return frame

    def _build_control_row(self) -> QHBoxLayout:
        ctrl = QHBoxLayout()

        self._play_btn = QPushButton("▶")
        self._play_btn.setFixedSize(34, 28)
        self._play_btn.clicked.connect(self._toggle_play)

        self._time_lbl = QLabel("--:-- / --:--")
        self._time_lbl.setFixedWidth(130)

        self._load_status = QLabel("")
        self._load_btn = QPushButton("プレビューを読み込む")
        self._load_btn.clicked.connect(self._load_preview)

        ctrl.addWidget(self._play_btn)
        ctrl.addWidget(self._time_lbl)
        ctrl.addStretch()
        ctrl.addWidget(self._load_status)
        ctrl.addWidget(self._load_btn)
        return ctrl

    # ------------------------------------------------------------------
    # プレビュー読み込み
    # ------------------------------------------------------------------

    def _load_preview(self) -> None:
        if not self._current_url:
            QMessageBox.warning(self, "URL 未入力", "上の URL 欄に URL を入力してください。")
            return
        self._load_btn.setEnabled(False)
        self._load_status.setText("取得中…")
        self._worker = _StreamUrlWorker(self._current_url, self._ytdlp_path)
        self._worker.url_ready.connect(self._on_stream_ready)
        self._worker.failed.connect(self._on_stream_failed)
        self._worker.start()

    def _on_stream_ready(self, stream_url: str) -> None:
        if self._player is None:
            return
        self._load_btn.setEnabled(True)
        self._load_status.setText("読み込み完了")
        self._player.setSource(QUrl(stream_url))

        # 開始時刻が指定されていればそこからシークして再生
        start_sec = _parse_seconds(self._start_edit.text())
        if start_sec is not None:
            self._player.setPosition(int(start_sec * 1000))
        self._player.play()

    def _on_stream_failed(self, error: str) -> None:
        self._load_btn.setEnabled(True)
        self._load_status.setText("エラー")
        QMessageBox.warning(self, "プレビューエラー", error)

    # ------------------------------------------------------------------
    # 再生コントロール
    # ------------------------------------------------------------------

    def _toggle_play(self) -> None:
        if self._player is None:
            return
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _on_slider_pressed(self) -> None:
        self._slider_dragging = True

    def _on_slider_released(self) -> None:
        assert self._player is not None
        self._slider_dragging = False
        self._player.setPosition(self._seek_slider.value())

    def _on_seek_moved(self, pos_ms: int) -> None:
        # ドラッグ中は再生位置を動かさず、時刻ラベルだけ更新する
        assert self._player is not None
        total = self._player.duration()
        self._time_lbl.setText(f"{_fmt(pos_ms / 1000)} / {_fmt(total / 1000)}")

    def _on_position_changed(self, pos_ms: int) -> None:
        assert self._player is not None
        if not self._slider_dragging:
            self._seek_slider.setValue(pos_ms)
        total = self._player.duration()
        self._time_lbl.setText(f"{_fmt(pos_ms / 1000)} / {_fmt(total / 1000)}")

    def _on_duration_changed(self, duration_ms: int) -> None:
        self._seek_slider.setRange(0, duration_ms)

    def _on_playback_state_changed(self, state: "QMediaPlayer.PlaybackState") -> None:
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self._play_btn.setText("⏸" if playing else "▶")

    # ------------------------------------------------------------------
    # 時刻設定 / シーク
    # ------------------------------------------------------------------

    def _set_start_from_player(self) -> None:
        if self._player is None:
            return
        self._start_edit.setText(_fmt(self._player.position() / 1000))

    def _set_end_from_player(self) -> None:
        if self._player is None:
            return
        self._end_edit.setText(_fmt(self._player.position() / 1000))

    def _seek_to_text(self, text: str) -> None:
        # 開始 / 終了の入力欄が変更されたときにプレーヤーを指定位置へシークする。
        if self._player is None:
            return
        seconds = _parse_seconds(text)
        if seconds is not None:
            self._player.setPosition(int(seconds * 1000))
