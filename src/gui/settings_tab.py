"""設定タブ: バイナリパス、aria2c、アップデート、インストール設定。"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,  # アップデート確認ダイアログで使用
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core._license import LICENSE_TEXT
from core.binary_manager import BinaryManager
from core.config import Config
from core.updater import APP_VERSION, OsakanaUpdater, YtDlpUpdater
from gui.style import DARK_STYLE, LIGHT_STYLE


class SettingsTab(QWidget):
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

        # スクロールエリアにグループをまとめる
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setSpacing(10)
        inner_layout.setContentsMargins(0, 0, 0, 0)

        inner_layout.addWidget(self._build_appearance_group())
        inner_layout.addWidget(self._build_paths_group())
        inner_layout.addWidget(self._build_filename_group())
        inner_layout.addWidget(self._build_download_ctrl_group())
        inner_layout.addWidget(self._build_subtitle_group())
        inner_layout.addWidget(self._build_postprocess_group())
        inner_layout.addWidget(self._build_network_group())
        inner_layout.addWidget(self._build_aria2c_group())
        inner_layout.addWidget(self._build_update_group())
        inner_layout.addWidget(self._build_install_group())
        inner_layout.addWidget(self._build_extra_args_group())
        inner_layout.addWidget(self._build_license_group())
        inner_layout.addStretch()

        scroll.setWidget(inner)
        root.addWidget(scroll)

    # --- 外観 ---

    def _build_appearance_group(self) -> QGroupBox:
        box = QGroupBox("外観")
        layout = QVBoxLayout(box)
        self._dark_theme_cb = QCheckBox("ダークテーマを使用する")
        self._dark_theme_cb.toggled.connect(self._on_dark_theme_toggled)
        layout.addWidget(self._dark_theme_cb)
        return box

    def _on_dark_theme_toggled(self, checked: bool) -> None:
        from typing import cast as _cast
        from PyQt6.QtWidgets import QApplication
        _cast(QApplication, QApplication.instance()).setStyleSheet(DARK_STYLE if checked else LIGHT_STYLE)

    # --- パス ---

    def _build_paths_group(self) -> QGroupBox:
        box = QGroupBox("バイナリパス")
        form = QFormLayout(box)

        self._ytdlp_edit  = self._path_row(form, "yt-dlp:",  "yt-dlp")
        self._ffmpeg_edit  = self._path_row(form, "ffmpeg:",  "ffmpeg")
        self._aria2c_edit  = self._path_row(form, "aria2c:",  "aria2c")
        return box

    def _path_row(self, form: QFormLayout, label: str, name: str) -> QLineEdit:
        edit = QLineEdit()
        edit.setPlaceholderText(f"{name} のパス（自動検出）")
        btn = QPushButton("参照…")
        btn.setFixedWidth(70)
        btn.clicked.connect(lambda _, e=edit: self._browse_binary(e))
        row = QWidget()
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(edit)
        hl.addWidget(btn)
        form.addRow(label, row)
        return edit

    # --- ファイル名テンプレート ---

    # yt-dlp の出力テンプレートプリセット（表示名, テンプレート文字列）
    _FILENAME_PRESETS = [
        ("タイトル [ID]",                     "%(title)s [%(id)s].%(ext)s"),
        ("タイトル",                           "%(title)s.%(ext)s"),
        ("投稿者 - タイトル",                  "%(uploader)s - %(title)s.%(ext)s"),
        ("日付 タイトル [ID]",                 "%(upload_date)s %(title)s [%(id)s].%(ext)s"),
        ("プレイリスト番号 タイトル",          "%(playlist_index)s - %(title)s.%(ext)s"),
        ("ID のみ",                            "%(id)s.%(ext)s"),
        ("カスタム…",                          ""),
    ]

    def _build_filename_group(self) -> QGroupBox:
        box = QGroupBox("ファイル名テンプレート")
        layout = QVBoxLayout(box)
        layout.setSpacing(6)

        # プリセット選択コンボ
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("プリセット:"))
        self._filename_preset_combo = QComboBox()
        for label, _ in self._FILENAME_PRESETS:
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
        hint = QLabel(
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
        hint.setWordWrap(True)
        hint.setOpenExternalLinks(False)
        layout.addWidget(hint)

        return box

    def _on_filename_preset_changed(self, index: int) -> None:
        _, tpl = self._FILENAME_PRESETS[index]
        if tpl:  # "カスタム…" 以外はテキスト欄を上書き
            # textChanged シグナルが再帰的に _on_filename_text_changed を呼ばないようブロック
            self._filename_edit.blockSignals(True)
            self._filename_edit.setText(tpl)
            self._filename_edit.blockSignals(False)

    def _on_filename_text_changed(self, text: str) -> None:
        """手入力されたら「カスタム…」を選択状態にする。"""
        for i, (_, tpl) in enumerate(self._FILENAME_PRESETS):
            if tpl == text:
                self._filename_preset_combo.blockSignals(True)
                self._filename_preset_combo.setCurrentIndex(i)
                self._filename_preset_combo.blockSignals(False)
                return
        # 一致するプリセットがなければ「カスタム…」
        self._filename_preset_combo.blockSignals(True)
        self._filename_preset_combo.setCurrentIndex(len(self._FILENAME_PRESETS) - 1)
        self._filename_preset_combo.blockSignals(False)

    # --- ダウンロード制御 ---

    def _build_download_ctrl_group(self) -> QGroupBox:
        box = QGroupBox("ダウンロード制御")
        form = QFormLayout(box)

        self._speed_limit_edit = QLineEdit()
        self._speed_limit_edit.setPlaceholderText("例: 5M, 1024K（空欄 = 制限なし）")
        form.addRow("速度制限:", self._speed_limit_edit)

        self._retries_spin = QSpinBox()
        self._retries_spin.setRange(1, 50)
        self._retries_spin.setSuffix(" 回")
        form.addRow("リトライ回数:", self._retries_spin)

        archive_row = QWidget()
        archive_hl = QHBoxLayout(archive_row)
        archive_hl.setContentsMargins(0, 0, 0, 0)
        self._archive_edit = QLineEdit()
        self._archive_edit.setPlaceholderText("ダウンロード済みURLを記録するファイル（空欄 = 無効）")
        archive_browse = QPushButton("参照…")
        archive_browse.setFixedWidth(70)
        archive_browse.clicked.connect(
            lambda: self._browse_file(self._archive_edit, "アーカイブファイルを選択", "テキストファイル (*.txt);;すべてのファイル (*)")
        )
        archive_hl.addWidget(self._archive_edit)
        archive_hl.addWidget(archive_browse)
        form.addRow("ダウンロードアーカイブ:", archive_row)

        return box

    # --- 字幕 ---

    def _build_subtitle_group(self) -> QGroupBox:
        box = QGroupBox("字幕")
        form = QFormLayout(box)

        self._sub_langs_edit = QLineEdit()
        self._sub_langs_edit.setPlaceholderText("例: ja,en（カンマ区切り）")
        form.addRow("言語:", self._sub_langs_edit)

        self._sub_format_combo = QComboBox()
        self._sub_format_combo.addItems(["srt", "ass", "vtt", "best"])
        form.addRow("字幕形式:", self._sub_format_combo)

        self._auto_subs_cb = QCheckBox("自動生成字幕も取得する（YouTube 等）")
        form.addRow("", self._auto_subs_cb)

        return box

    # --- 後処理 ---

    def _build_postprocess_group(self) -> QGroupBox:
        box = QGroupBox("後処理")
        layout = QVBoxLayout(box)

        self._embed_thumbnail_cb = QCheckBox("サムネイルを埋め込む（--embed-thumbnail）")
        self._embed_metadata_cb  = QCheckBox("メタデータを埋め込む（タイトル・投稿者・日付など）")
        layout.addWidget(self._embed_thumbnail_cb)
        layout.addWidget(self._embed_metadata_cb)

        sb_row = QHBoxLayout()
        sb_row.addWidget(QLabel("SponsorBlock:"))
        self._sponsorblock_combo = QComboBox()
        self._sponsorblock_combo.addItems([
            "off（無効）",
            "sponsor（スポンサー区間のみ）",
            "default（sponsor / selfpromo / interaction / intro / outro / preview / filler）",
            "all（すべてのカテゴリ）",
        ])
        sb_row.addWidget(self._sponsorblock_combo)
        sb_row.addStretch()
        layout.addLayout(sb_row)

        return box

    # --- ネットワーク ---

    def _build_network_group(self) -> QGroupBox:
        box = QGroupBox("ネットワーク")
        form = QFormLayout(box)

        self._proxy_edit = QLineEdit()
        self._proxy_edit.setPlaceholderText("例: http://proxy:8080（空欄 = 無効）")
        form.addRow("プロキシ:", self._proxy_edit)

        self._cookies_browser_combo = QComboBox()
        self._cookies_browser_combo.addItems([
            "なし",
            "chrome", "firefox", "edge", "safari",
            "brave", "opera", "chromium", "vivaldi", "whale",
        ])
        form.addRow("クッキー取得元ブラウザ:", self._cookies_browser_combo)

        return box

    # --- aria2c 設定 ---

    def _build_aria2c_group(self) -> QGroupBox:
        box = QGroupBox("aria2c")
        layout = QVBoxLayout(box)

        self._aria2c_enabled_cb = QCheckBox("aria2c を使用する（ダウンロード高速化）")
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

    # --- アップデート ---

    def _build_update_group(self) -> QGroupBox:
        box = QGroupBox("アップデート")
        layout = QVBoxLayout(box)

        # ── yt-dlp ──────────────────────────────────────────────────
        layout.addWidget(QLabel("<b>yt-dlp</b>"))
        self._auto_update_cb = QCheckBox("起動時に自動でアップデートを確認する")
        layout.addWidget(self._auto_update_cb)

        ytdlp_row = QWidget()
        ytdlp_hl = QHBoxLayout(ytdlp_row)
        ytdlp_hl.setContentsMargins(0, 0, 0, 0)
        check_btn = QPushButton("今すぐ確認…")
        check_btn.clicked.connect(self._check_update_now)
        self._update_status_label = QLabel("")
        ytdlp_hl.addWidget(check_btn)
        ytdlp_hl.addWidget(self._update_status_label)
        ytdlp_hl.addStretch()
        layout.addWidget(ytdlp_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Plain)
        layout.addWidget(sep)

        # ── Osakana ─────────────────────────────────────────────────
        layout.addWidget(QLabel("<b>Osakana</b>"))
        self._auto_update_app_cb = QCheckBox("起動時に自動でアップデートを確認する")
        layout.addWidget(self._auto_update_app_cb)

        app_row = QWidget()
        app_hl = QHBoxLayout(app_row)
        app_hl.setContentsMargins(0, 0, 0, 0)
        check_app_btn = QPushButton("今すぐ確認…")
        check_app_btn.clicked.connect(self._check_osakana_update_now)
        self._app_update_status_label = QLabel("")
        app_hl.addWidget(check_app_btn)
        app_hl.addWidget(self._app_update_status_label)
        app_hl.addStretch()
        layout.addWidget(app_row)

        return box

    # --- カスタムオプション ---

    def _build_extra_args_group(self) -> QGroupBox:
        box = QGroupBox("カスタムオプション")
        layout = QVBoxLayout(box)

        self._extra_args_edit = QLineEdit()
        self._extra_args_edit.setPlaceholderText(
            "例: --no-mtime --write-description（空欄 = 無効）"
        )
        layout.addWidget(self._extra_args_edit)

        hint = QLabel(
            "<small><span style='color:#a6adc8;'>"
            "yt-dlp に追加で渡すコマンドラインオプションをスペース区切りで入力してください。"
            "スペースを含む値はクォートで囲んでください（例: --match-title \"foo bar\"）。"
            "</span></small>"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        return box

    # --- ライセンス ---

    def _build_license_group(self) -> QGroupBox:
        box = QGroupBox("ライセンス")
        layout = QVBoxLayout(box)

        view = QPlainTextEdit()
        view.setPlainText(LICENSE_TEXT)
        view.setReadOnly(True)
        view.setFixedHeight(200)
        layout.addWidget(view)

        return box

    # --- インストールモード ---

    def _build_install_group(self) -> QGroupBox:
        box = QGroupBox("インストールモード")
        layout = QVBoxLayout(box)
        self._auto_install_rb   = QRadioButton("自動インストール")
        self._manual_install_rb = QRadioButton("手動インストール（通知のみ）")
        layout.addWidget(self._auto_install_rb)
        layout.addWidget(self._manual_install_rb)
        return box

    # ------------------------------------------------------------------
    # 読み込み / 保存
    # ------------------------------------------------------------------

    # SponsorBlock コンボのインデックス ↔ 設定値の対応
    _SB_VALUES = ["off", "sponsor", "default", "all"]

    def _load_values(self) -> None:
        # 外観
        self._dark_theme_cb.blockSignals(True)
        self._dark_theme_cb.setChecked(bool(self._config.get("IsDarkThemeEnabled", True)))
        self._dark_theme_cb.blockSignals(False)

        self._ytdlp_edit.setText(self._config.get("YtdlpPath", ""))
        self._ffmpeg_edit.setText(self._config.get("FfmpegPath", ""))
        self._aria2c_edit.setText(self._config.get("Aria2cPath", ""))

        tpl = self._config.get("FilenameTemplate", "%(title)s [%(id)s].%(ext)s")
        self._filename_edit.setText(tpl)

        # ダウンロード制御
        self._speed_limit_edit.setText(self._config.get("SpeedLimit", ""))
        self._retries_spin.setValue(self._config.get("Retries", 10))
        self._archive_edit.setText(self._config.get("DownloadArchive", ""))

        # 字幕
        self._sub_langs_edit.setText(self._config.get("SubLangs", "ja,en"))
        sub_format = self._config.get("SubFormat", "srt")
        idx = self._sub_format_combo.findText(sub_format)
        self._sub_format_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._auto_subs_cb.setChecked(bool(self._config.get("AutoSubs")))

        # 後処理
        self._embed_thumbnail_cb.setChecked(bool(self._config.get("EmbedThumbnail")))
        self._embed_metadata_cb.setChecked(bool(self._config.get("EmbedMetadata")))
        sb = self._config.get("SponsorBlock", "off")
        sb_idx = self._SB_VALUES.index(sb) if sb in self._SB_VALUES else 0
        self._sponsorblock_combo.setCurrentIndex(sb_idx)

        # ネットワーク
        self._proxy_edit.setText(self._config.get("Proxy", ""))
        browser = self._config.get("CookiesBrowser", "")
        cb_idx = self._cookies_browser_combo.findText(browser or "なし")
        self._cookies_browser_combo.setCurrentIndex(cb_idx if cb_idx >= 0 else 0)

        aria2c_on = bool(self._config.get("IsAria2cEnabled"))
        self._aria2c_enabled_cb.setChecked(aria2c_on)
        self._aria2c_sub.setEnabled(aria2c_on)
        self._aria2c_conn_spin.setValue(self._config.get("Aria2cConnections", 16))
        self._max_dl_spin.setValue(self._config.get("MaxParallelDownloads", 2))

        self._auto_update_cb.setChecked(bool(self._config.get("AutoUpdate")))
        self._auto_update_app_cb.setChecked(bool(self._config.get("AutoUpdateApp")))

        if self._config.get("AutoInstall"):
            self._auto_install_rb.setChecked(True)
        else:
            self._manual_install_rb.setChecked(True)

        self._extra_args_edit.setText(self._config.get("ExtraArgs", ""))

    def _connect_auto_save(self) -> None:
        """全ウィジェットの変更シグナルを _save に接続する。"""
        # テキスト入力欄はフォーカスを外したとき / Enter を押したときに保存
        for edit in (
            self._ytdlp_edit, self._ffmpeg_edit, self._aria2c_edit,
            self._filename_edit, self._speed_limit_edit, self._archive_edit,
            self._sub_langs_edit, self._proxy_edit, self._extra_args_edit,
        ):
            edit.editingFinished.connect(self._save)

        # スピンボックス・コンボボックス・チェックボックス・ラジオボタンは即時保存
        self._retries_spin.valueChanged.connect(self._save)
        self._aria2c_conn_spin.valueChanged.connect(self._save)
        self._max_dl_spin.valueChanged.connect(self._save)
        self._sub_format_combo.currentIndexChanged.connect(self._save)
        self._sponsorblock_combo.currentIndexChanged.connect(self._save)
        self._cookies_browser_combo.currentIndexChanged.connect(self._save)
        self._auto_subs_cb.toggled.connect(self._save)
        self._embed_thumbnail_cb.toggled.connect(self._save)
        self._embed_metadata_cb.toggled.connect(self._save)
        self._aria2c_enabled_cb.toggled.connect(self._save)
        self._dark_theme_cb.toggled.connect(self._save)
        self._auto_update_cb.toggled.connect(self._save)
        self._auto_update_app_cb.toggled.connect(self._save)
        self._auto_install_rb.toggled.connect(self._save)
        self._manual_install_rb.toggled.connect(self._save)

    def _save(self) -> None:
        browser = self._cookies_browser_combo.currentText()
        self._config.update(
            {
                "YtdlpPath":            self._ytdlp_edit.text().strip(),
                "FfmpegPath":           self._ffmpeg_edit.text().strip(),
                "Aria2cPath":           self._aria2c_edit.text().strip(),
                "FilenameTemplate":     self._filename_edit.text().strip() or "%(title)s [%(id)s].%(ext)s",
                # ダウンロード制御
                "SpeedLimit":           self._speed_limit_edit.text().strip(),
                "Retries":              self._retries_spin.value(),
                "DownloadArchive":      self._archive_edit.text().strip(),
                # 字幕
                "SubLangs":             self._sub_langs_edit.text().strip() or "ja,en",
                "SubFormat":            self._sub_format_combo.currentText(),
                "AutoSubs":             self._auto_subs_cb.isChecked(),
                # 後処理
                "EmbedThumbnail":       self._embed_thumbnail_cb.isChecked(),
                "EmbedMetadata":        self._embed_metadata_cb.isChecked(),
                "SponsorBlock":         self._SB_VALUES[self._sponsorblock_combo.currentIndex()],
                # ネットワーク
                "Proxy":                self._proxy_edit.text().strip(),
                "CookiesBrowser":       "" if browser == "なし" else browser,
                # その他
                "IsAria2cEnabled":      self._aria2c_enabled_cb.isChecked(),
                "Aria2cConnections":    self._aria2c_conn_spin.value(),
                "MaxParallelDownloads": self._max_dl_spin.value(),
                "AutoUpdate":           self._auto_update_cb.isChecked(),
                "AutoUpdateApp":        self._auto_update_app_cb.isChecked(),
                "AutoInstall":          self._auto_install_rb.isChecked(),
                "ExtraArgs":            self._extra_args_edit.text().strip(),
                # 外観
                "IsDarkThemeEnabled":   self._dark_theme_cb.isChecked(),
            }
        )

    # ------------------------------------------------------------------
    # スロット
    # ------------------------------------------------------------------

    def _on_aria2c_toggled(self, checked: bool) -> None:
        self._aria2c_sub.setEnabled(checked)

    def _browse_binary(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "バイナリを選択", edit.text())
        if path:
            edit.setText(path)

    def _browse_file(self, edit: QLineEdit, title: str, filter_str: str) -> None:
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
