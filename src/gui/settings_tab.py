# 設定タブ: バイナリパス / aria2c / アップデート / インストール設定。
from __future__ import annotations

import shutil
from typing import List, Optional, Tuple, cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core._license import LICENSE_TEXT
from core.binary_manager import INSTALL_DIR, BinaryManager
from core.config import CONFIG_PATH, Config
from core.downloader import DEFAULT_FILENAME_TEMPLATE
from core.updater import APP_VERSION, OsakanaUpdater, YtDlpUpdater
from gui.style import DARK_STYLE, LIGHT_STYLE


# ─────────────────────────────────────────────────────────────────────
# 表示用定数
# ─────────────────────────────────────────────────────────────────────

# yt-dlp の出力テンプレートプリセット (表示名, テンプレート文字列)
_FILENAME_PRESETS: List[Tuple[str, str]] = [
    ("タイトル [ID]",                "%(title)s [%(id)s].%(ext)s"),
    ("タイトル",                      "%(title)s.%(ext)s"),
    ("投稿者 - タイトル",             "%(uploader)s - %(title)s.%(ext)s"),
    ("日付 タイトル [ID]",            "%(upload_date)s %(title)s [%(id)s].%(ext)s"),
    ("プレイリスト番号 タイトル",     "%(playlist_index)s - %(title)s.%(ext)s"),
    ("ID のみ",                       "%(id)s.%(ext)s"),
    ("カスタム…",                     ""),
]

# SponsorBlock コンボのインデックス ↔ 設定値
_SB_VALUES = ["off", "sponsor", "default", "all"]

# HwAccel コンボのインデックス ↔ 設定値
_HW_VALUES = ["none", "nvidia", "amd", "intel"]

_FILENAME_HINT_HTML = (
    "<small><span style='color:#a6adc8;'>"
    "主なプレースホルダー: "
    "<b>%(title)s</b> タイトル　"
    "<b>%(id)s</b> ID　"
    "<b>%(uploader)s</b> 投稿者　"
    "<b>%(upload_date)s</b> 投稿日 (YYYYMMDD)　"
    "<b>%(playlist_index)s</b> 再生リスト番号　"
    "<b>%(ext)s</b> 拡張子"
    "</span></small>"
)

_EXTRA_ARGS_HINT_HTML = (
    "<small><span style='color:#a6adc8;'>"
    "yt-dlp に追加で渡すコマンドラインオプションをスペース区切りで入力してください。"
    "スペースを含む値はクォートで囲んでください (例: --match-title \"foo bar\")。"
    "</span></small>"
)


def _purge_osakana_data() -> List[str]:
    # 設定ファイルとバイナリを全削除する。エラーが出たパスのリストを返す
    # (空なら全て成功)。
    errors: List[str] = []

    if CONFIG_PATH.exists():
        try:
            CONFIG_PATH.unlink()
        except OSError as exc:
            errors.append(f"{CONFIG_PATH}: {exc}")

    # ~/.osakana/bin を丸ごと削除し、親ディレクトリも空なら片付ける。
    install_root = INSTALL_DIR.parent  # ~/.osakana
    if INSTALL_DIR.exists():
        try:
            shutil.rmtree(INSTALL_DIR)
        except OSError as exc:
            errors.append(f"{INSTALL_DIR}: {exc}")

    if install_root.exists():
        try:
            # bin 以外に何も無ければ ~/.osakana も削除する。
            if not any(install_root.iterdir()):
                install_root.rmdir()
        except OSError as exc:
            errors.append(f"{install_root}: {exc}")

    return errors


# ─────────────────────────────────────────────────────────────────────
# SettingsTab
# ─────────────────────────────────────────────────────────────────────

class SettingsTab(QWidget):
    # 設定値の編集 UI と Config の自動同期を担うタブ。

    def __init__(
        self,
        config: Config,
        binary_manager: BinaryManager,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._bm = binary_manager
        self._setup_ui()
        self._load_values()
        self._connect_auto_save()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setSpacing(10)
        inner_layout.setContentsMargins(0, 0, 0, 0)

        # グループの追加順序がそのまま画面上の順序になる
        for builder in (
            self._build_appearance_group,
            self._build_paths_group,
            self._build_filename_group,
            self._build_download_ctrl_group,
            self._build_subtitle_group,
            self._build_postprocess_group,
            self._build_network_group,
            self._build_aria2c_group,
            self._build_update_group,
            self._build_install_group,
            self._build_extra_args_group,
            self._build_reset_group,
            self._build_license_group,
        ):
            inner_layout.addWidget(builder())
        inner_layout.addStretch()

        scroll.setWidget(inner)
        root.addWidget(scroll)

    # ── 外観 ──────────────────────────────────────────────────

    def _build_appearance_group(self) -> QGroupBox:
        box = QGroupBox("外観")
        layout = QVBoxLayout(box)
        self._dark_theme_cb = QCheckBox("ダークテーマを使用する")
        self._dark_theme_cb.toggled.connect(self._on_dark_theme_toggled)
        layout.addWidget(self._dark_theme_cb)
        return box

    def _on_dark_theme_toggled(self, checked: bool) -> None:
        cast(QApplication, QApplication.instance()).setStyleSheet(
            DARK_STYLE if checked else LIGHT_STYLE
        )

    # ── バイナリパス ───────────────────────────────────────────

    def _build_paths_group(self) -> QGroupBox:
        box = QGroupBox("バイナリパス")
        form = QFormLayout(box)
        self._ytdlp_edit  = self._path_row(form, "yt-dlp:",  "yt-dlp")
        self._ffmpeg_edit = self._path_row(form, "ffmpeg:",  "ffmpeg")
        self._deno_edit   = self._path_row(form, "deno:",    "deno")
        self._aria2c_edit = self._path_row(form, "aria2c:",  "aria2c")
        return box

    def _path_row(self, form: QFormLayout, label: str, name: str) -> QLineEdit:
        edit = QLineEdit()
        edit.setPlaceholderText(f"{name} のパス (自動検出)")

        browse = QPushButton("参照…")
        browse.setFixedWidth(70)
        browse.clicked.connect(lambda _, e=edit: self._browse_binary(e))

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(edit)
        row_layout.addWidget(browse)
        form.addRow(label, row)
        return edit

    # ── ファイル名テンプレート ─────────────────────────────────

    def _build_filename_group(self) -> QGroupBox:
        box = QGroupBox("ファイル名テンプレート")
        layout = QVBoxLayout(box)
        layout.setSpacing(6)

        # プリセット選択
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("プリセット:"))
        self._filename_preset_combo = QComboBox()
        for label, _ in _FILENAME_PRESETS:
            self._filename_preset_combo.addItem(label)
        self._filename_preset_combo.currentIndexChanged.connect(self._on_filename_preset_changed)
        preset_row.addWidget(self._filename_preset_combo)
        preset_row.addStretch()
        layout.addLayout(preset_row)

        # テンプレート入力欄
        self._filename_edit = QLineEdit()
        self._filename_edit.setPlaceholderText("例: %(title)s [%(id)s].%(ext)s")
        self._filename_edit.textChanged.connect(self._on_filename_text_changed)
        layout.addWidget(self._filename_edit)

        # 使用可能なプレースホルダーのヒント
        hint = QLabel(_FILENAME_HINT_HTML)
        hint.setWordWrap(True)
        hint.setOpenExternalLinks(False)
        layout.addWidget(hint)

        return box

    def _on_filename_preset_changed(self, index: int) -> None:
        _, template = _FILENAME_PRESETS[index]
        if not template:  # "カスタム…"
            return
        # textChanged → _on_filename_text_changed の再帰呼び出しを回避
        self._filename_edit.blockSignals(True)
        self._filename_edit.setText(template)
        self._filename_edit.blockSignals(False)

    def _on_filename_text_changed(self, text: str) -> None:
        # 手入力されたら一致するプリセットを選択、なければ「カスタム…」。
        target = len(_FILENAME_PRESETS) - 1  # default: 「カスタム…」
        for i, (_, template) in enumerate(_FILENAME_PRESETS):
            if template == text:
                target = i
                break
        self._filename_preset_combo.blockSignals(True)
        self._filename_preset_combo.setCurrentIndex(target)
        self._filename_preset_combo.blockSignals(False)

    # ── ダウンロード制御 ────────────────────────────────────────

    def _build_download_ctrl_group(self) -> QGroupBox:
        box = QGroupBox("ダウンロード制御")
        form = QFormLayout(box)

        self._speed_limit_edit = QLineEdit()
        self._speed_limit_edit.setPlaceholderText("例: 5M, 1024K (空欄 = 制限なし)")
        form.addRow("速度制限:", self._speed_limit_edit)

        self._retries_spin = QSpinBox()
        self._retries_spin.setRange(1, 50)
        self._retries_spin.setSuffix(" 回")
        form.addRow("リトライ回数:", self._retries_spin)

        # ダウンロードアーカイブ (パス + 参照ボタン)
        self._archive_edit = QLineEdit()
        self._archive_edit.setPlaceholderText("ダウンロード済み URL を記録するファイル (空欄 = 無効)")

        archive_browse = QPushButton("参照…")
        archive_browse.setFixedWidth(70)
        archive_browse.clicked.connect(
            lambda: self._browse_save_file(
                self._archive_edit,
                "アーカイブファイルを選択",
                "テキストファイル (*.txt);;すべてのファイル (*)",
            )
        )

        archive_row = QWidget()
        archive_layout = QHBoxLayout(archive_row)
        archive_layout.setContentsMargins(0, 0, 0, 0)
        archive_layout.addWidget(self._archive_edit)
        archive_layout.addWidget(archive_browse)
        form.addRow("ダウンロードアーカイブ:", archive_row)

        return box

    # ── 字幕 ──────────────────────────────────────────────────

    def _build_subtitle_group(self) -> QGroupBox:
        box = QGroupBox("字幕")
        form = QFormLayout(box)

        self._sub_langs_edit = QLineEdit()
        self._sub_langs_edit.setPlaceholderText("例: ja,en (カンマ区切り)")
        form.addRow("言語:", self._sub_langs_edit)

        self._sub_format_combo = QComboBox()
        self._sub_format_combo.addItems(["srt", "ass", "vtt", "best"])
        form.addRow("字幕形式:", self._sub_format_combo)

        self._auto_subs_cb = QCheckBox("自動生成字幕も取得する (YouTube 等)")
        form.addRow("", self._auto_subs_cb)

        return box

    # ── 後処理 ────────────────────────────────────────────────

    def _build_postprocess_group(self) -> QGroupBox:
        box = QGroupBox("後処理")
        layout = QVBoxLayout(box)

        self._embed_thumbnail_cb = QCheckBox("サムネイルを埋め込む (--embed-thumbnail)")
        self._embed_metadata_cb  = QCheckBox("メタデータを埋め込む (タイトル・投稿者・日付など)")
        layout.addWidget(self._embed_thumbnail_cb)
        layout.addWidget(self._embed_metadata_cb)

        self._sponsorblock_combo = QComboBox()
        self._sponsorblock_combo.addItems([
            "off (無効)",
            "sponsor (スポンサー区間のみ)",
            "default (sponsor / selfpromo / interaction / intro / outro / preview / filler)",
            "all (すべてのカテゴリ)",
        ])
        layout.addLayout(self._labeled_row("SponsorBlock:", self._sponsorblock_combo))

        self._hw_accel_combo = QComboBox()
        self._hw_accel_combo.addItems([
            "none (無効・ソフトウェア)",
            "nvidia (NVENC)",
            "amd (AMF)",
            "intel (QSV)",
        ])
        layout.addLayout(self._labeled_row("ハードウェアエンコード (H.265):", self._hw_accel_combo))

        return box

    @staticmethod
    def _labeled_row(label: str, widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(widget)
        row.addStretch()
        return row

    # ── ネットワーク ──────────────────────────────────────────

    def _build_network_group(self) -> QGroupBox:
        box = QGroupBox("ネットワーク")
        form = QFormLayout(box)

        self._proxy_edit = QLineEdit()
        self._proxy_edit.setPlaceholderText("例: http://proxy:8080 (空欄 = 無効)")
        form.addRow("プロキシ:", self._proxy_edit)

        self._cookies_browser_combo = QComboBox()
        self._cookies_browser_combo.addItems([
            "なし",
            "chrome", "firefox", "edge", "safari",
            "brave", "opera", "chromium", "vivaldi", "whale",
        ])
        form.addRow("クッキー取得元ブラウザ:", self._cookies_browser_combo)

        return box

    # ── aria2c ────────────────────────────────────────────────

    def _build_aria2c_group(self) -> QGroupBox:
        box = QGroupBox("aria2c")
        layout = QVBoxLayout(box)

        self._aria2c_enabled_cb = QCheckBox("aria2c を使用する (ダウンロード高速化)")
        self._aria2c_enabled_cb.toggled.connect(self._on_aria2c_toggled)
        layout.addWidget(self._aria2c_enabled_cb)

        self._aria2c_sub = QWidget()
        sub_layout = QFormLayout(self._aria2c_sub)
        sub_layout.setContentsMargins(20, 0, 0, 0)

        self._aria2c_conn_spin = QSpinBox()
        self._aria2c_conn_spin.setRange(1, 64)
        self._aria2c_conn_spin.setSuffix(" 接続")
        sub_layout.addRow("サーバー当たりの並列接続数:", self._aria2c_conn_spin)

        self._max_dl_spin = QSpinBox()
        self._max_dl_spin.setRange(1, 16)
        self._max_dl_spin.setSuffix(" 同時")
        sub_layout.addRow("最大同時ダウンロード数:", self._max_dl_spin)

        self._aria2c_sub.setEnabled(False)
        layout.addWidget(self._aria2c_sub)
        return box

    # ── アップデート ──────────────────────────────────────────

    def _build_update_group(self) -> QGroupBox:
        box = QGroupBox("アップデート")
        layout = QVBoxLayout(box)

        # ── yt-dlp ───────────────────────────────
        layout.addWidget(QLabel("<b>yt-dlp</b>"))
        self._auto_update_cb = QCheckBox("起動時に自動でアップデートを確認する")
        layout.addWidget(self._auto_update_cb)

        self._update_status_label = QLabel("")
        layout.addWidget(
            self._build_check_row("今すぐ確認…", self._check_update_now, self._update_status_label)
        )

        # 区切り線
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Plain)
        layout.addWidget(sep)

        # ── Osakana ──────────────────────────────
        layout.addWidget(QLabel("<b>Osakana</b>"))
        self._auto_update_app_cb = QCheckBox("起動時に自動でアップデートを確認する")
        layout.addWidget(self._auto_update_app_cb)

        self._app_update_status_label = QLabel("")
        layout.addWidget(
            self._build_check_row(
                "今すぐ確認…", self._check_osakana_update_now, self._app_update_status_label
            )
        )

        return box

    @staticmethod
    def _build_check_row(button_label: str, slot, status_label: QLabel) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)

        button = QPushButton(button_label)
        button.clicked.connect(slot)
        layout.addWidget(button)
        layout.addWidget(status_label)
        layout.addStretch()
        return row

    # ── インストールモード ────────────────────────────────────

    def _build_install_group(self) -> QGroupBox:
        box = QGroupBox("インストールモード")
        layout = QVBoxLayout(box)
        self._auto_install_rb   = QRadioButton("自動インストール")
        self._manual_install_rb = QRadioButton("手動インストール (通知のみ)")
        layout.addWidget(self._auto_install_rb)
        layout.addWidget(self._manual_install_rb)
        return box

    # ── カスタムオプション ────────────────────────────────────

    def _build_extra_args_group(self) -> QGroupBox:
        box = QGroupBox("カスタムオプション")
        layout = QVBoxLayout(box)

        self._extra_args_edit = QLineEdit()
        self._extra_args_edit.setPlaceholderText(
            "例: --no-mtime --write-description (空欄 = 無効)"
        )
        layout.addWidget(self._extra_args_edit)

        hint = QLabel(_EXTRA_ARGS_HINT_HTML)
        hint.setWordWrap(True)
        layout.addWidget(hint)
        return box

    # ── 初期化 ────────────────────────────────────────────────

    def _build_reset_group(self) -> QGroupBox:
        box = QGroupBox("初期化")
        layout = QVBoxLayout(box)

        desc = QLabel(
            "設定ファイル (<code>~/.osakana/config</code>) と、"
            "Osakana がインストールしたバイナリ (<code>~/.osakana/bin/</code>) を"
            "すべて削除して初期状態に戻します。<br>"
            "<b>この操作は取り消せません。</b>"
        )
        desc.setWordWrap(True)
        desc.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(desc)

        reset_btn = QPushButton("設定とバイナリを削除して初期化…")
        reset_btn.clicked.connect(self._on_reset_clicked)
        layout.addWidget(reset_btn)
        return box

    def _on_reset_clicked(self) -> None:
        # 2 段階確認でユーザの誤操作を防ぐ。
        first = QMessageBox.warning(
            self,
            "初期化の確認",
            "設定ファイルとインストール済みバイナリをすべて削除します。\n"
            "この操作は取り消せません。\n\n本当に実行しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if first != QMessageBox.StandardButton.Yes:
            return

        second = QMessageBox.warning(
            self,
            "最終確認",
            f"以下を削除します:\n\n"
            f"  • {CONFIG_PATH}\n"
            f"  • {INSTALL_DIR}\n\n"
            f"削除後、アプリは自動的に終了します。",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if second != QMessageBox.StandardButton.Ok:
            return

        errors = _purge_osakana_data()
        if errors:
            QMessageBox.critical(
                self,
                "初期化エラー",
                "一部のファイルを削除できませんでした:\n\n" + "\n".join(errors),
            )
            return

        QMessageBox.information(
            self,
            "初期化完了",
            "設定とバイナリを削除しました。アプリを終了します。\n"
            "次回起動時にセットアップウィザードが再度表示されます。",
        )
        QApplication.quit()

    # ── ライセンス ────────────────────────────────────────────

    def _build_license_group(self) -> QGroupBox:
        box = QGroupBox("ライセンス")
        layout = QVBoxLayout(box)

        view = QPlainTextEdit()
        view.setPlainText(LICENSE_TEXT)
        view.setReadOnly(True)
        view.setFixedHeight(200)
        layout.addWidget(view)
        return box

    # ------------------------------------------------------------------
    # 読み込み / 保存
    # ------------------------------------------------------------------

    def _load_values(self) -> None:
        # 外観
        self._dark_theme_cb.blockSignals(True)
        self._dark_theme_cb.setChecked(bool(self._config.get("IsDarkThemeEnabled", True)))
        self._dark_theme_cb.blockSignals(False)

        # バイナリパス
        self._ytdlp_edit.setText(self._config.get("YtdlpPath", ""))
        self._ffmpeg_edit.setText(self._config.get("FfmpegPath", ""))
        self._deno_edit.setText(self._config.get("DenoPath", ""))
        self._aria2c_edit.setText(self._config.get("Aria2cPath", ""))

        # ファイル名
        self._filename_edit.setText(
            self._config.get("FilenameTemplate", DEFAULT_FILENAME_TEMPLATE)
        )

        # ダウンロード制御
        self._speed_limit_edit.setText(self._config.get("SpeedLimit", ""))
        self._retries_spin.setValue(self._config.get("Retries", 10))
        self._archive_edit.setText(self._config.get("DownloadArchive", ""))

        # 字幕
        self._sub_langs_edit.setText(self._config.get("SubLangs", "ja,en"))
        sub_format = self._config.get("SubFormat", "srt")
        sub_idx = self._sub_format_combo.findText(sub_format)
        self._sub_format_combo.setCurrentIndex(sub_idx if sub_idx >= 0 else 0)
        self._auto_subs_cb.setChecked(bool(self._config.get("AutoSubs")))

        # 後処理
        self._embed_thumbnail_cb.setChecked(bool(self._config.get("EmbedThumbnail")))
        self._embed_metadata_cb.setChecked(bool(self._config.get("EmbedMetadata")))
        self._sponsorblock_combo.setCurrentIndex(self._lookup_index(_SB_VALUES, self._config.get("SponsorBlock", "off")))
        self._hw_accel_combo.setCurrentIndex(self._lookup_index(_HW_VALUES, self._config.get("HwAccel", "none")))

        # ネットワーク
        self._proxy_edit.setText(self._config.get("Proxy", ""))
        browser = self._config.get("CookiesBrowser", "")
        cb_idx = self._cookies_browser_combo.findText(browser or "なし")
        self._cookies_browser_combo.setCurrentIndex(cb_idx if cb_idx >= 0 else 0)

        # aria2c
        aria2c_on = bool(self._config.get("IsAria2cEnabled"))
        self._aria2c_enabled_cb.setChecked(aria2c_on)
        self._aria2c_sub.setEnabled(aria2c_on)
        self._aria2c_conn_spin.setValue(self._config.get("Aria2cConnections", 16))
        self._max_dl_spin.setValue(self._config.get("MaxParallelDownloads", 2))

        # アップデート
        self._auto_update_cb.setChecked(bool(self._config.get("AutoUpdate")))
        self._auto_update_app_cb.setChecked(bool(self._config.get("AutoUpdateApp")))

        # インストールモード
        if self._config.get("AutoInstall"):
            self._auto_install_rb.setChecked(True)
        else:
            self._manual_install_rb.setChecked(True)

        # その他
        self._extra_args_edit.setText(self._config.get("ExtraArgs", ""))

    @staticmethod
    def _lookup_index(values: List[str], target: str) -> int:
        return values.index(target) if target in values else 0

    def _connect_auto_save(self) -> None:
        # 全ウィジェットの変更シグナルを _save に接続する。
        # テキスト入力欄はフォーカスを外したとき / Enter で保存
        for edit in (
            self._ytdlp_edit, self._ffmpeg_edit, self._deno_edit, self._aria2c_edit,
            self._filename_edit, self._speed_limit_edit, self._archive_edit,
            self._sub_langs_edit, self._proxy_edit, self._extra_args_edit,
        ):
            edit.editingFinished.connect(self._save)

        # スピンボックス・コンボボックス・チェックボックス・ラジオボタンは即時保存
        for spin in (self._retries_spin, self._aria2c_conn_spin, self._max_dl_spin):
            spin.valueChanged.connect(self._save)

        for combo in (
            self._sub_format_combo,
            self._sponsorblock_combo,
            self._hw_accel_combo,
            self._cookies_browser_combo,
        ):
            combo.currentIndexChanged.connect(self._save)

        for cb in (
            self._auto_subs_cb,
            self._embed_thumbnail_cb,
            self._embed_metadata_cb,
            self._aria2c_enabled_cb,
            self._dark_theme_cb,
            self._auto_update_cb,
            self._auto_update_app_cb,
        ):
            cb.toggled.connect(self._save)

        for rb in (self._auto_install_rb, self._manual_install_rb):
            rb.toggled.connect(self._save)

    def _save(self) -> None:
        browser = self._cookies_browser_combo.currentText()
        self._config.update({
            # ── バイナリパス ───────────────────────────
            "YtdlpPath":            self._ytdlp_edit.text().strip(),
            "FfmpegPath":           self._ffmpeg_edit.text().strip(),
            "DenoPath":             self._deno_edit.text().strip(),
            "Aria2cPath":           self._aria2c_edit.text().strip(),
            # ── ファイル名 ─────────────────────────────
            "FilenameTemplate":     self._filename_edit.text().strip() or DEFAULT_FILENAME_TEMPLATE,
            # ── ダウンロード制御 ───────────────────────
            "SpeedLimit":           self._speed_limit_edit.text().strip(),
            "Retries":              self._retries_spin.value(),
            "DownloadArchive":      self._archive_edit.text().strip(),
            # ── 字幕 ───────────────────────────────────
            "SubLangs":             self._sub_langs_edit.text().strip() or "ja,en",
            "SubFormat":            self._sub_format_combo.currentText(),
            "AutoSubs":             self._auto_subs_cb.isChecked(),
            # ── 後処理 ─────────────────────────────────
            "EmbedThumbnail":       self._embed_thumbnail_cb.isChecked(),
            "EmbedMetadata":        self._embed_metadata_cb.isChecked(),
            "SponsorBlock":         _SB_VALUES[self._sponsorblock_combo.currentIndex()],
            "HwAccel":              _HW_VALUES[self._hw_accel_combo.currentIndex()],
            # ── ネットワーク ───────────────────────────
            "Proxy":                self._proxy_edit.text().strip(),
            "CookiesBrowser":       "" if browser == "なし" else browser,
            # ── aria2c ─────────────────────────────────
            "IsAria2cEnabled":      self._aria2c_enabled_cb.isChecked(),
            "Aria2cConnections":    self._aria2c_conn_spin.value(),
            "MaxParallelDownloads": self._max_dl_spin.value(),
            # ── アップデート / インストール ────────────
            "AutoUpdate":           self._auto_update_cb.isChecked(),
            "AutoUpdateApp":        self._auto_update_app_cb.isChecked(),
            "AutoInstall":          self._auto_install_rb.isChecked(),
            # ── その他 ─────────────────────────────────
            "ExtraArgs":            self._extra_args_edit.text().strip(),
            "IsDarkThemeEnabled":   self._dark_theme_cb.isChecked(),
        })

    # ------------------------------------------------------------------
    # スロット
    # ------------------------------------------------------------------

    def _on_aria2c_toggled(self, checked: bool) -> None:
        self._aria2c_sub.setEnabled(checked)
        if checked and not self._bm.find("aria2c"):
            self._prompt_install_aria2c()

    def _prompt_install_aria2c(self) -> None:
        from core.platform_detector import detect as detect_platform
        from gui.setup_wizard import SetupWizard

        answer = QMessageBox.question(
            self,
            "aria2c が見つかりません",
            "aria2c がインストールされていません。\n今すぐインストールしますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        wizard = SetupWizard(
            missing=["aria2c"],
            manager=self._bm,
            config=self._config,
            platform=detect_platform(),
            parent=self,
        )
        wizard.exec()

    def _browse_binary(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "バイナリを選択", edit.text())
        if path:
            edit.setText(path)

    def _browse_save_file(self, edit: QLineEdit, title: str, filter_str: str) -> None:
        path, _ = QFileDialog.getSaveFileName(self, title, edit.text(), filter_str)
        if path:
            edit.setText(path)

    def _check_update_now(self) -> None:
        ytdlp_path = self._ytdlp_edit.text().strip() or self._config.get("YtdlpPath", "")
        if not ytdlp_path:
            QMessageBox.warning(self, "エラー", "yt-dlp のパスが設定されていません。")
            return

        self._update_status_label.setText("確認中…")
        try:
            updater = YtDlpUpdater(ytdlp_path)
            current = updater.current_version()
            latest  = updater.latest_version()

            if not updater.needs_update():
                self._update_status_label.setText(f"最新です ({current})")
                return

            answer = QMessageBox.question(
                self,
                "アップデートが利用可能",
                f"現在: {current}\n最新: {latest}\n\n今すぐ更新しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._update_status_label.setText("更新中…")
                output = updater.update_output()
                self._update_status_label.setText("更新完了")
                QMessageBox.information(self, "更新完了", output[:800])
            else:
                self._update_status_label.setText("")
        except Exception as exc:
            self._update_status_label.setText("エラー")
            QMessageBox.critical(self, "アップデート確認エラー", str(exc))

    def _check_osakana_update_now(self) -> None:
        self._app_update_status_label.setText("確認中…")
        try:
            updater = OsakanaUpdater()
            if not updater.needs_update():
                self._app_update_status_label.setText(f"最新です ({APP_VERSION})")
                return

            latest = updater.latest_version()
            self._app_update_status_label.setText(f"v{latest} が利用可能")
            QMessageBox.information(
                self,
                "Osakana アップデートが利用可能",
                f"現在: {APP_VERSION}\n最新: {latest}\n\n"
                f"リリースページからダウンロードしてください:\n{updater.release_url()}",
            )
        except Exception as exc:
            self._app_update_status_label.setText("エラー")
            QMessageBox.critical(self, "アップデート確認エラー", str(exc))
