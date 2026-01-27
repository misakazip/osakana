"""設定タブ: バイナリパス、aria2c、アップデート、インストール設定。"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.binary_manager import BinaryManager
from core.config import Config
from core.updater import YtDlpUpdater


class SettingsTab(QWidget):
    def __init__(
        self,
        config: Config,
        binary_manager: BinaryManager,
        parent: QWidget = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._bm = binary_manager
        self._setup_ui()
        self._load_values()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(12, 12, 12, 12)

        root.addWidget(self._build_paths_group())
        root.addWidget(self._build_filename_group())
        root.addWidget(self._build_aria2c_group())
        root.addWidget(self._build_update_group())
        root.addWidget(self._build_install_group())
        root.addStretch()

        save_btn = QPushButton("設定を保存")
        save_btn.setFixedHeight(34)
        save_btn.clicked.connect(self._save)
        root.addWidget(save_btn)

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
        box = QGroupBox("yt-dlp アップデート")
        layout = QVBoxLayout(box)

        self._auto_update_cb = QCheckBox("起動時に自動でアップデートを確認する")
        layout.addWidget(self._auto_update_cb)

        row = QWidget()
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 0, 0, 0)
        check_btn = QPushButton("今すぐ確認…")
        check_btn.clicked.connect(self._check_update_now)
        self._update_status_label = QLabel("")
        hl.addWidget(check_btn)
        hl.addWidget(self._update_status_label)
        hl.addStretch()
        layout.addWidget(row)
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

    def _load_values(self) -> None:
        self._ytdlp_edit.setText(self._config.get("YtdlpPath", ""))
        self._ffmpeg_edit.setText(self._config.get("FfmpegPath", ""))
        self._aria2c_edit.setText(self._config.get("Aria2cPath", ""))

        tpl = self._config.get("FilenameTemplate", "%(title)s [%(id)s].%(ext)s")
        self._filename_edit.setText(tpl)  # _on_filename_text_changed がコンボを自動同期

        aria2c_on = bool(self._config.get("IsAria2cEnabled"))
        self._aria2c_enabled_cb.setChecked(aria2c_on)
        self._aria2c_sub.setEnabled(aria2c_on)
        self._aria2c_conn_spin.setValue(self._config.get("Aria2cConnections", 16))
        self._max_dl_spin.setValue(self._config.get("MaxParallelDownloads", 2))

        self._auto_update_cb.setChecked(bool(self._config.get("AutoUpdate")))

        if self._config.get("AutoInstall"):
            self._auto_install_rb.setChecked(True)
        else:
            self._manual_install_rb.setChecked(True)

    def _save(self) -> None:
        self._config.update(
            {
                "YtdlpPath": self._ytdlp_edit.text().strip(),
                "FfmpegPath": self._ffmpeg_edit.text().strip(),
                "Aria2cPath": self._aria2c_edit.text().strip(),
                "FilenameTemplate": self._filename_edit.text().strip() or "%(title)s [%(id)s].%(ext)s",
                "IsAria2cEnabled": self._aria2c_enabled_cb.isChecked(),
                "Aria2cConnections": self._aria2c_conn_spin.value(),
                "MaxParallelDownloads": self._max_dl_spin.value(),
                "AutoUpdate": self._auto_update_cb.isChecked(),
                "AutoInstall": self._auto_install_rb.isChecked(),
            }
        )
        QMessageBox.information(self, "保存完了", "設定を保存しました。")

    # ------------------------------------------------------------------
    # スロット
    # ------------------------------------------------------------------

    def _on_aria2c_toggled(self, checked: bool) -> None:
        self._aria2c_sub.setEnabled(checked)

    def _browse_binary(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "バイナリを選択", edit.text())
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
