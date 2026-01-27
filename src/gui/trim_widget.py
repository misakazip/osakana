"""TrimWidget — 動画プレビュープレーヤー付きの切り抜き範囲セレクタ。

レイアウト:
  [開始: HH:MM:SS] [←現在位置]   [終了: HH:MM:SS] [←現在位置]
  ┌──────────────── video ─────────────────────────────────┐
  │                                                         │
  └─────────────────────────────────────────────────────────┘
  ──────────────●──────────────  シークバー
  [▶]  00:01:23 / 00:10:00      [プレビューを読み込む]  ステータス

GroupBox はチェック可能で、チェックを外すと内容が非表示になる。
"""
from __future__ import annotations

import re
from typing import Optional

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

# Qt Multimedia のインポートを試みる — 利用不可の場合は機能を縮退させる
try:
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PyQt6.QtMultimediaWidgets import QVideoWidget
    _MULTIMEDIA_OK = True
except ImportError:
    _MULTIMEDIA_OK = False

# ── 時刻ヘルパー ──────────────────────────────────────────────────────

_TIME_RE = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2})$")


def _parse_seconds(text: str) -> Optional[float]:
    """"HH:MM:SS"、"MM:SS"、または秒数の文字列を float に変換する。"""
    t = text.strip()
    if not t:
        return None
    m = _TIME_RE.match(t)
    if m:
        h  = int(m.group(1) or 0)
        mi = int(m.group(2))
        s  = int(m.group(3))
        return h * 3600 + mi * 60 + s
    try:
        return float(t)
    except ValueError:
        return None


def _fmt(seconds: float) -> str:
    """浮動小数点の秒数を "HH:MM:SS"（1時間未満は "MM:SS"）に変換する。"""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


# ── バックグラウンドワーカー: yt-dlp -g でストリームURLを取得 ────────────────

class _StreamUrlWorker(QThread):
    url_ready = pyqtSignal(str)
    failed    = pyqtSignal(str)

    def __init__(self, url: str, ytdlp_path: str) -> None:
        super().__init__()
        self._url       = url
        self._ytdlp_path = ytdlp_path

    def run(self) -> None:
        import subprocess
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
                self.failed.emit(result.stderr.strip() or "ストリームURLの取得に失敗しました")
        except Exception as exc:
            self.failed.emit(str(exc))


# ── メインウィジェット ───────────────────────────────────────────────────────

class TrimWidget(QGroupBox):
    """折りたたみ可能な切り抜き範囲セレクタ（動画プレビュー付き）。"""

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__("切り抜き", parent)
        self.setCheckable(True)
        self.setChecked(False)

        self._ytdlp_path: str = "yt-dlp"
        self._current_url: str = ""
        self._worker: Optional[_StreamUrlWorker] = None
        self._slider_dragging = False

        # URLや時刻入力後の自動プレビュー用デバウンスタイマー（1.5秒）
        self._url_timer = QTimer(self)
        self._url_timer.setSingleShot(True)
        self._url_timer.setInterval(1500)
        self._url_timer.timeout.connect(self._load_preview)

        self._setup_ui()

        # グループのチェックを外したときにコンテンツを非表示にする
        self.toggled.connect(self._content.setVisible)
        self._content.setVisible(False)

        # 開始・終了時刻の変更でプレーヤーをシーク
        self._start_edit.textChanged.connect(self._on_start_time_changed)
        self._end_edit.textChanged.connect(self._on_end_time_changed)

    # ── 公開API ────────────────────────────────────────────────────

    def set_ytdlp_path(self, path: str) -> None:
        self._ytdlp_path = path or "yt-dlp"

    def set_url(self, url: str) -> None:
        if url == self._current_url:
            return
        self._current_url = url
        # URLが変わったらデバウンスタイマーを起動（グループが有効な場合のみ）
        if self.isChecked() and url and _MULTIMEDIA_OK:
            self._url_timer.start()

    def trim_start(self) -> str:
        return self._start_edit.text().strip()

    def trim_end(self) -> str:
        return self._end_edit.text().strip()

    def is_trim_enabled(self) -> bool:
        return self.isChecked()

    # ── UI 構築 ───────────────────────────────────────────────

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

        row.addWidget(QLabel("開始:"))
        self._start_edit = QLineEdit()
        self._start_edit.setPlaceholderText("HH:MM:SS")
        self._start_edit.setFixedWidth(85)
        self._start_btn = QPushButton("← 現在位置")
        self._start_btn.setFixedWidth(88)
        self._start_btn.setToolTip("プレーヤーの現在位置を開始点に設定")
        self._start_btn.clicked.connect(self._set_start_from_player)
        row.addWidget(self._start_edit)
        row.addWidget(self._start_btn)

        row.addSpacing(16)

        row.addWidget(QLabel("終了:"))
        self._end_edit = QLineEdit()
        self._end_edit.setPlaceholderText("HH:MM:SS")
        self._end_edit.setFixedWidth(85)
        self._end_btn = QPushButton("← 現在位置")
        self._end_btn.setFixedWidth(88)
        self._end_btn.setToolTip("プレーヤーの現在位置を終了点に設定")
        self._end_btn.clicked.connect(self._set_end_from_player)
        row.addWidget(self._end_edit)
        row.addWidget(self._end_btn)

        row.addStretch()
        return row

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

        # 動画出力
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

        # コントロール行
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
        layout.addLayout(ctrl)

        # メディアプレーヤー
        self._player       = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        self._player.setVideoOutput(self._video_widget)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self._on_playback_state_changed)

        return frame

    # ── プレビュー読み込み ───────────────────────────────────────────────

    def _load_preview(self) -> None:
        if not self._current_url:
            QMessageBox.warning(self, "URL 未入力", "上のURL欄にURLを入力してください。")
            return
        self._load_btn.setEnabled(False)
        self._load_status.setText("取得中…")
        self._worker = _StreamUrlWorker(self._current_url, self._ytdlp_path)
        self._worker.url_ready.connect(self._on_stream_ready)
        self._worker.failed.connect(self._on_stream_failed)
        self._worker.start()

    def _on_stream_ready(self, stream_url: str) -> None:
        self._load_btn.setEnabled(True)
        self._load_status.setText("読み込み完了")
        self._player.setSource(QUrl(stream_url))
        # 開始時刻が指定されていればシークしてから再生する
        start_sec = _parse_seconds(self._start_edit.text())
        if start_sec is not None:
            self._player.setPosition(int(start_sec * 1000))
        self._player.play()

    def _on_stream_failed(self, error: str) -> None:
        self._load_btn.setEnabled(True)
        self._load_status.setText("エラー")
        QMessageBox.warning(self, "プレビューエラー", error)

    # ── 再生コントロール ──────────────────────────────────────────────

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
        self._slider_dragging = False
        self._player.setPosition(self._seek_slider.value())

    def _on_seek_moved(self, pos_ms: int) -> None:
        # ドラッグ中は再生位置を動かさず時刻ラベルだけ更新する
        total = self._player.duration()
        self._time_lbl.setText(f"{_fmt(pos_ms / 1000)} / {_fmt(total / 1000)}")

    def _on_position_changed(self, pos_ms: int) -> None:
        if not self._slider_dragging:
            self._seek_slider.setValue(pos_ms)
        total = self._player.duration()
        self._time_lbl.setText(f"{_fmt(pos_ms / 1000)} / {_fmt(total / 1000)}")

    def _on_duration_changed(self, duration_ms: int) -> None:
        self._seek_slider.setRange(0, duration_ms)

    def _on_playback_state_changed(self, state: "QMediaPlayer.PlaybackState") -> None:
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self._play_btn.setText("⏸" if playing else "▶")

    # ── 時刻設定ボタン ─────────────────────────────────────────────

    def _set_start_from_player(self) -> None:
        if self._player is None:
            return
        self._start_edit.setText(_fmt(self._player.position() / 1000))

    def _set_end_from_player(self) -> None:
        if self._player is None:
            return
        self._end_edit.setText(_fmt(self._player.position() / 1000))

    # ── 時刻入力によるシーク ──────────────────────────────────────────

    def _on_start_time_changed(self, text: str) -> None:
        """開始時刻が変更されたらプレーヤーをその位置にシークする。"""
        if self._player is None:
            return
        sec = _parse_seconds(text)
        if sec is not None:
            self._player.setPosition(int(sec * 1000))

    def _on_end_time_changed(self, text: str) -> None:
        """終了時刻が変更されたらプレーヤーをその位置にシークする。"""
        if self._player is None:
            return
        sec = _parse_seconds(text)
        if sec is not None:
            self._player.setPosition(int(sec * 1000))
