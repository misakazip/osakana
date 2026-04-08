# メインダウンロードタブ: URL 入力 / フォーマット / オプション / キュー表示。
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.config import Config
from core.downloader import (
    AUDIO_FORMATS,
    CONTAINERS,
    DEFAULT_FILENAME_TEMPLATE,
    VIDEO_QUALITIES,
    DownloadManager,
    DownloadTask,
)
from gui.queue_widget import QueueWidget
from gui.trim_widget import TrimWidget

# ─────────────────────────────────────────────────────────────────────
# プレイリスト / チャンネル URL の判定
# ─────────────────────────────────────────────────────────────────────

# 各サイトでまとめてダウンロードを示すパターン
_BULK_URL_RE = re.compile(
    r"[?&]list="                       # YouTube プレイリスト (?list= / &list=)
    r"|/playlist\?"                    # /playlist?
    r"|/channel/"                      # YouTube チャンネル /channel/UC...
    r"|youtube\.com/c/"                # /c/ChannelName
    r"|youtube\.com/@"                 # /@handle
    r"|youtube\.com/user/"             # /user/name
    r"|/videos$"                       # チャンネルの動画一覧ページ末尾
    r"|nicovideo\.jp/user/\d+/video"   # ニコニコ ユーザー投稿動画
    r"|nicovideo\.jp/series/"          # ニコニコ シリーズ
    r"|twitch\.tv/[^/]+/videos",       # Twitch チャンネル動画一覧
    re.IGNORECASE,
)


def _has_bulk_url(urls: Iterable[str]) -> bool:
    # URL リストにプレイリストやチャンネル URL が含まれるか判定する。
    return any(_BULK_URL_RE.search(u) for u in urls)


# ─────────────────────────────────────────────────────────────────────
# DownloadTab
# ─────────────────────────────────────────────────────────────────────

class DownloadTab(QWidget):
    # URL の入力からキュー監視までを 1 画面でまかなうメインタブ。

    def __init__(
        self,
        manager: DownloadManager,
        config: Config,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._manager = manager
        self._config = config
        self._setup_ui()
        self._connect_manager()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(10, 10, 10, 10)

        # ページ全体をスクロールエリアに収める
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setSpacing(8)
        inner_layout.setContentsMargins(0, 0, 0, 0)

        inner_layout.addWidget(self._build_url_group())
        inner_layout.addWidget(self._build_format_group())
        inner_layout.addWidget(self._build_options_group())
        inner_layout.addWidget(self._build_output_row())
        inner_layout.addLayout(self._build_action_row())
        inner_layout.addWidget(self._build_trim_widget())
        inner_layout.addWidget(self._build_queue_group())
        inner_layout.addWidget(self._build_raw_log_group())

        scroll.setWidget(inner)
        root.addWidget(scroll)
        root.addWidget(self._build_overall_progress())

    def _build_url_group(self) -> QGroupBox:
        box = QGroupBox("URL")
        layout = QVBoxLayout(box)

        self._url_edit = QPlainTextEdit()
        self._url_edit.setPlaceholderText("ダウンロードしたい URL を入力してください (複数行可)")
        self._url_edit.setFixedHeight(80)
        layout.addWidget(self._url_edit)

        load_file_btn = QPushButton("ファイルから読み込む…")
        load_file_btn.setToolTip("URL が 1 行ずつ記述されたテキストファイルを選択します")
        load_file_btn.clicked.connect(self._load_urls_from_file)

        clear_url_btn = QPushButton("クリア")
        clear_url_btn.setFixedWidth(70)
        clear_url_btn.clicked.connect(self._url_edit.clear)

        btn_row = QHBoxLayout()
        btn_row.addWidget(load_file_btn)
        btn_row.addStretch()
        btn_row.addWidget(clear_url_btn)
        layout.addLayout(btn_row)

        return box

    def _build_format_group(self) -> QGroupBox:
        box = QGroupBox("フォーマット")
        layout = QHBoxLayout(box)

        layout.addWidget(QLabel("画質:"))
        self._quality_combo = QComboBox()
        self._quality_combo.addItems(VIDEO_QUALITIES)
        layout.addWidget(self._quality_combo)

        layout.addWidget(QLabel("コンテナ:"))
        self._container_combo = QComboBox()
        self._container_combo.addItems(CONTAINERS)
        layout.addWidget(self._container_combo)

        # 音声フォーマット (音声のみチェック時のみ表示)
        self._audio_fmt_label = QLabel("音声フォーマット:")
        self._audio_fmt_combo = QComboBox()
        self._audio_fmt_combo.addItems(AUDIO_FORMATS)
        self._audio_fmt_label.setVisible(False)
        self._audio_fmt_combo.setVisible(False)
        layout.addWidget(self._audio_fmt_label)
        layout.addWidget(self._audio_fmt_combo)

        layout.addStretch()
        return box

    def _build_options_group(self) -> QGroupBox:
        box = QGroupBox("オプション")
        layout = QHBoxLayout(box)

        self._audio_only_cb = QCheckBox("音声のみ")
        self._playlist_cb   = QCheckBox("プレイリスト全体")
        self._subs_cb       = QCheckBox("字幕を埋め込む")

        self._h265_cb = QCheckBox("H.265 (HEVC) に変換")
        self._h265_cb.setToolTip(
            "ffmpeg を使って動画を H.265/HEVC に再エンコードします (変換に時間がかかります)"
        )

        self._antibot_cb = QCheckBox("bot 検知回避")
        self._antibot_cb.setToolTip(
            "レート制限とリクエスト間隔を設けて bot 検知を回避します\n"
            "(--rate-limit 5M  --min-sleep-interval 15  --max-sleep-interval 45)"
        )

        self._members_only_cb = QCheckBox("メンバーシップのみ")
        self._members_only_cb.setToolTip(
            "チャンネルメンバー限定の動画のみダウンロードします\n"
            '(--match-filter "availability=subscriber_only")'
        )

        self._notify_cb = QCheckBox("完了時に通知")
        self._notify_cb.setToolTip("ダウンロード完了時にデスクトップ通知を表示します")
        self._notify_cb.setChecked(bool(self._config.get("DesktopNotify")))
        self._notify_cb.toggled.connect(
            lambda v: self._config.set("DesktopNotify", v)
        )

        self._audio_only_cb.toggled.connect(self._on_audio_only_toggled)

        for cb in (
            self._audio_only_cb,
            self._playlist_cb,
            self._subs_cb,
            self._h265_cb,
            self._antibot_cb,
            self._members_only_cb,
            self._notify_cb,
        ):
            layout.addWidget(cb)

        # aria2c 並列接続数 (設定で有効化されている場合のみ表示)
        self._aria2c_label = QLabel("aria2c 並列接続数:")
        self._aria2c_spin = QSpinBox()
        self._aria2c_spin.setRange(1, 64)
        self._aria2c_spin.setValue(self._config.get("Aria2cConnections", 16))
        self._aria2c_spin.valueChanged.connect(
            lambda v: self._config.set("Aria2cConnections", v)
        )
        aria2c_visible = bool(self._config.get("IsAria2cEnabled"))
        self._aria2c_label.setVisible(aria2c_visible)
        self._aria2c_spin.setVisible(aria2c_visible)

        layout.addStretch()
        layout.addWidget(self._aria2c_label)
        layout.addWidget(self._aria2c_spin)

        return box

    def _build_output_row(self) -> QGroupBox:
        box = QGroupBox("保存先")
        layout = QHBoxLayout(box)

        default_dir = self._config.get("OutputDirectory", str(Path.home() / "Downloads"))
        self._output_edit = QLineEdit(default_dir)

        browse_btn = QPushButton("参照…")
        browse_btn.setFixedWidth(70)
        browse_btn.clicked.connect(self._browse_output)

        layout.addWidget(self._output_edit)
        layout.addWidget(browse_btn)
        return box

    def _build_action_row(self) -> QHBoxLayout:
        layout = QHBoxLayout()

        self._dl_btn = QPushButton("ダウンロード")
        self._dl_btn.setFixedHeight(36)
        self._dl_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._dl_btn.clicked.connect(self._on_download)

        clear_btn = QPushButton("完了済みを削除")
        clear_btn.setFixedHeight(36)
        clear_btn.clicked.connect(self._on_clear_finished)

        layout.addWidget(self._dl_btn)
        layout.addWidget(clear_btn)
        return layout

    def _build_trim_widget(self) -> TrimWidget:
        self._trim = TrimWidget()
        self._trim.set_ytdlp_path(self._config.get("YtdlpPath", "yt-dlp"))
        # URL フィールドの変更を都度 TrimWidget に反映 (最初の 1 行を使用)
        self._url_edit.textChanged.connect(self._sync_trim_url)
        return self._trim

    def _build_queue_group(self) -> QGroupBox:
        box = QGroupBox("キュー")
        layout = QVBoxLayout(box)
        self._queue = QueueWidget()
        layout.addWidget(self._queue)
        return box

    def _build_overall_progress(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(8)

        self._overall_bar = QProgressBar()
        self._overall_bar.setRange(0, 100)
        self._overall_bar.setValue(0)
        self._overall_bar.setTextVisible(True)
        self._overall_bar.setFixedHeight(18)

        self._overall_label = QLabel("0 / 0")
        self._overall_label.setFixedWidth(60)
        self._overall_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._overall_bar)
        layout.addWidget(self._overall_label)
        return widget

    def _build_raw_log_group(self) -> QGroupBox:
        box = QGroupBox("RAW ログ")
        box.setCheckable(True)
        box.setChecked(False)

        layout = QVBoxLayout(box)

        self._raw_log = QPlainTextEdit()
        self._raw_log.setReadOnly(True)
        self._raw_log.setMaximumBlockCount(2000)  # メモリ節約のため上限設定

        mono = QFont("Monospace")
        mono.setStyleHint(QFont.StyleHint.TypeWriter)
        self._raw_log.setFont(mono)
        self._raw_log.setFixedHeight(160)

        clear_log_btn = QPushButton("ログをクリア")
        clear_log_btn.setFixedWidth(110)
        clear_log_btn.clicked.connect(self._raw_log.clear)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(clear_log_btn)

        layout.addWidget(self._raw_log)
        layout.addLayout(btn_row)

        # GroupBox のチェック状態でログ本体を表示/非表示
        box.toggled.connect(self._raw_log.setVisible)
        box.toggled.connect(clear_log_btn.setVisible)
        self._raw_log.setVisible(False)
        clear_log_btn.setVisible(False)

        self._raw_log_box = box
        return box

    # ------------------------------------------------------------------
    # シグナル接続
    # ------------------------------------------------------------------

    def _connect_manager(self) -> None:
        self._manager.task_added.connect(self._on_task_added)
        self._manager.progress_updated.connect(self._queue.update_progress)
        # 各タスクの進捗率変化も全体バーに反映する (完了カウントだけだと
        # 2 本目以降のダウンロード中にバーが停止して見えるため)。
        self._manager.progress_updated.connect(lambda *_: self._update_overall_progress())
        self._manager.status_changed.connect(self._queue.update_status)
        self._manager.status_changed.connect(lambda *_: self._update_overall_progress())
        self._manager.title_fetched.connect(self._queue.update_title)
        self._manager.raw_output.connect(self._on_raw_output)
        self._queue.cancel_requested.connect(self._manager.cancel)

    # ------------------------------------------------------------------
    # スロット
    # ------------------------------------------------------------------

    def _update_overall_progress(self) -> None:
        done, total = self._queue.get_counts()
        self._overall_label.setText(f"{done} / {total}")
        # 完了カウントではなく各行の進捗バーの合計で塗る。
        self._overall_bar.setValue(int(self._queue.get_overall_progress()))

    def _on_task_added(self, task: DownloadTask) -> None:
        display = task.url[:80] + ("…" if len(task.url) > 80 else "")
        self._queue.add_task(task.id, display)
        self._update_overall_progress()

    def _on_download(self) -> None:
        urls = self._collect_urls()
        if not urls:
            return

        output_dir = self._output_edit.text().strip() or str(Path.home() / "Downloads")
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        avoid_bot = self._antibot_cb.isChecked()
        # プレイリスト / チャンネルが含まれていてかつ未指定なら確認ダイアログ
        if not avoid_bot and _has_bulk_url(urls):
            avoid_bot = self._confirm_avoid_bot()
            if avoid_bot:
                self._antibot_cb.setChecked(True)

        for url in urls:
            self._manager.add(self._build_task(url, output_dir, avoid_bot))

        self._url_edit.clear()

    def _collect_urls(self) -> List[str]:
        return [
            line.strip()
            for line in self._url_edit.toPlainText().splitlines()
            if line.strip()
        ]

    def _confirm_avoid_bot(self) -> bool:
        answer = QMessageBox.question(
            self,
            "bot 検知回避を有効にしますか？",
            "プレイリストまたはチャンネルの URL が検出されました。\n\n"
            "大量ダウンロード時はサーバー側で bot 判定される場合があります。\n"
            "レート制限とリクエスト間隔を設けて検知を回避しますか？\n\n"
            "  --rate-limit 5M\n"
            "  --min-sleep-interval 15\n"
            "  --max-sleep-interval 45",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,  # デフォルト: Yes
        )
        return answer == QMessageBox.StandardButton.Yes

    def _build_task(self, url: str, output_dir: str, avoid_bot: bool) -> DownloadTask:
        trim_enabled = self._trim.is_trim_enabled()
        return DownloadTask(
            url=url,
            output_dir=output_dir,
            quality=self._quality_combo.currentText(),
            audio_only=self._audio_only_cb.isChecked(),
            audio_format=self._audio_fmt_combo.currentText(),
            container=self._container_combo.currentText(),
            embed_subtitles=self._subs_cb.isChecked(),
            playlist=self._playlist_cb.isChecked(),
            convert_h265=self._h265_cb.isChecked(),
            avoid_bot_detection=avoid_bot,
            members_only=self._members_only_cb.isChecked(),
            trim_start=self._trim.trim_start() if trim_enabled else "",
            trim_end=self._trim.trim_end() if trim_enabled else "",
            filename_template=self._config.get("FilenameTemplate", DEFAULT_FILENAME_TEMPLATE),
        )

    def _on_clear_finished(self) -> None:
        self._queue.remove_finished()
        self._update_overall_progress()

    def _sync_trim_url(self) -> None:
        first_line = self._url_edit.toPlainText().splitlines()
        self._trim.set_url(first_line[0].strip() if first_line else "")

    def _on_raw_output(self, task_id: str, line: str) -> None:
        if self._raw_log_box.isChecked():
            self._raw_log.appendPlainText(line)

    def _load_urls_from_file(self) -> None:
        # テキストファイルから URL を読み込んで URL 欄に追加する。
        path, _ = QFileDialog.getOpenFileName(
            self, "URL ファイルを選択", "", "テキストファイル (*.txt);;すべてのファイル (*)"
        )
        if not path:
            return

        try:
            lines = Path(path).read_text(encoding="utf-8").splitlines()
            urls = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
            if not urls:
                return
            existing = self._url_edit.toPlainText().strip()
            combined = (existing + "\n" if existing else "") + "\n".join(urls)
            self._url_edit.setPlainText(combined)
        except Exception as exc:
            QMessageBox.warning(self, "ファイル読み込みエラー", str(exc))

    def _on_audio_only_toggled(self, checked: bool) -> None:
        self._audio_fmt_label.setVisible(checked)
        self._audio_fmt_combo.setVisible(checked)
        self._quality_combo.setEnabled(not checked)
        self._container_combo.setEnabled(not checked)
        self._subs_cb.setEnabled(not checked)
        self._h265_cb.setEnabled(not checked)

    def _browse_output(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "保存先フォルダを選択", self._output_edit.text()
        )
        if directory:
            self._output_edit.setText(directory)
            self._config.set("OutputDirectory", directory)
