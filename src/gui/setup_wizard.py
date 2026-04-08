# 初回起動 / バイナリ欠落時のセットアップウィザード。
#
# フロー:
#
# 1. 不足している必須バイナリを一覧表示する
# 2. 手動 / 自動インストールをユーザに選択させる
# 3. (自動選択時) 各バイナリをプログレスバー付きでインストールする
# 4. yt-dlp の自動アップデートを有効にするか確認する
# 5. 閉じる
from __future__ import annotations

from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.binary_manager import BinaryManager
from core.config import Config
from core.platform_detector import PlatformInfo


# ─────────────────────────────────────────────────────────────────────
# バックグラウンドインストールワーカー
# ─────────────────────────────────────────────────────────────────────

class _InstallWorker(QThread):
    # 単一バイナリをバックグラウンドでインストールする QThread。

    progress     = pyqtSignal(str, int)   # バイナリ名, 0–100
    log_message  = pyqtSignal(str)
    finished_ok  = pyqtSignal(str, str)   # バイナリ名, インストール先パス
    finished_err = pyqtSignal(str, str)   # バイナリ名, エラーメッセージ

    def __init__(
        self,
        name: str,
        manager: BinaryManager,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._manager = manager

    def run(self) -> None:
        try:
            self.log_message.emit(f"{self._name} をインストール中…")
            path = self._manager.install(
                self._name,
                progress=lambda pct: self.progress.emit(self._name, pct),
            )
            if path:
                self.finished_ok.emit(self._name, path)
            else:
                self.finished_err.emit(self._name, "パスを取得できませんでした")
        except Exception as exc:
            self.finished_err.emit(self._name, str(exc))


# ─────────────────────────────────────────────────────────────────────
# SetupWizard
# ─────────────────────────────────────────────────────────────────────

class SetupWizard(QDialog):
    # バイナリインストールを案内するモーダルダイアログ。

    def __init__(
        self,
        missing: List[str],
        manager: BinaryManager,
        config: Config,
        platform: PlatformInfo,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._missing  = list(missing)
        self._manager  = manager
        self._config   = config
        self._platform = platform

        self._workers: List[_InstallWorker] = []
        self._bars: Dict[str, QProgressBar] = {}
        self._pending: List[str] = []

        self.setWindowTitle("セットアップ — Osakana")
        self.setMinimumWidth(520)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_missing_label())
        layout.addWidget(self._build_mode_group())
        layout.addWidget(self._build_progress_group())
        layout.addWidget(self._build_log())

        # yt-dlp 自動アップデートのオプション
        self._auto_update_cb = QCheckBox("yt-dlp の自動アップデートを有効にする")
        self._auto_update_cb.setChecked(False)
        layout.addWidget(self._auto_update_cb)

        # スキップ時に次回以降もウィザードを開かないためのオプション
        self._dont_show_again_cb = QCheckBox(
            "次回アプリ起動時にこのセットアップを表示しない"
        )
        self._dont_show_again_cb.setChecked(
            bool(self._config.get("SkipSetupWizard"))
        )
        layout.addWidget(self._dont_show_again_cb)

        layout.addWidget(self._build_button_box())

    def _build_header(self) -> QLabel:
        label = QLabel("<b>必要なバイナリが見つかりません</b>")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    def _build_missing_label(self) -> QLabel:
        bullet_list = "  •  " + "\n  •  ".join(self._missing)
        label = QLabel(f"以下のバイナリが見つかりませんでした:\n{bullet_list}")
        label.setWordWrap(True)
        return label

    def _build_mode_group(self) -> QGroupBox:
        box = QGroupBox("インストール方法")
        layout = QVBoxLayout(box)

        self._auto_rb   = QRadioButton("自動でインストールする (推奨)")
        self._manual_rb = QRadioButton("手動でインストールする (後で設定から確認)")
        self._auto_rb.setChecked(True)

        group = QButtonGroup(self)
        group.addButton(self._auto_rb)
        group.addButton(self._manual_rb)

        layout.addWidget(self._auto_rb)
        layout.addWidget(self._manual_rb)
        return box

    def _build_progress_group(self) -> QGroupBox:
        self._progress_group = QGroupBox("インストール進捗")
        layout = QVBoxLayout(self._progress_group)

        for name in self._missing:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)

            label = QLabel(f"{name}:")
            label.setFixedWidth(70)

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)

            row_layout.addWidget(label)
            row_layout.addWidget(bar)
            layout.addWidget(row)
            self._bars[name] = bar

        self._progress_group.setVisible(False)
        return self._progress_group

    def _build_log(self) -> QTextEdit:
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(90)
        self._log.setVisible(False)
        return self._log

    def _build_button_box(self) -> QDialogButtonBox:
        self._btn_box = QDialogButtonBox()

        self._install_btn = QPushButton("インストール開始")
        self._install_btn.setDefault(True)
        self._install_btn.clicked.connect(self._on_install_clicked)

        self._skip_btn = QPushButton("スキップして起動")
        self._skip_btn.clicked.connect(self._on_skip_clicked)

        self._btn_box.addButton(self._install_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        self._btn_box.addButton(self._skip_btn,    QDialogButtonBox.ButtonRole.RejectRole)
        return self._btn_box

    # ------------------------------------------------------------------
    # インストール制御
    # ------------------------------------------------------------------

    def _on_install_clicked(self) -> None:
        if self._manual_rb.isChecked():
            self._config.set("AutoInstall", False)
            self._finish()
            return

        # 自動インストール開始
        self._config.set("AutoInstall", True)
        self._install_btn.setEnabled(False)
        self._skip_btn.setEnabled(False)
        self._progress_group.setVisible(True)
        self._log.setVisible(True)
        self._pending = list(self._missing)
        self._install_next()

    def _install_next(self) -> None:
        # キューの先頭のバイナリをインストールする。空なら完了処理へ。
        if not self._pending:
            self._on_all_done()
            return

        name = self._pending[0]
        worker = _InstallWorker(name, self._manager, parent=self)
        worker.progress.connect(self._on_progress)
        worker.log_message.connect(self._append_log)
        worker.finished_ok.connect(self._on_worker_ok)
        worker.finished_err.connect(self._on_worker_err)
        self._workers.append(worker)
        worker.start()

    def _on_progress(self, name: str, pct: int) -> None:
        bar = self._bars.get(name)
        if bar is not None:
            bar.setValue(pct)

    def _on_worker_ok(self, name: str, path: str) -> None:
        self._append_log(f"✓ {name} → {path}")
        self._pending.pop(0)
        self._install_next()

    def _on_worker_err(self, name: str, error: str) -> None:
        self._append_log(f"✗ {name}: {error}")
        self._pending.pop(0)
        self._install_next()

    def _on_all_done(self) -> None:
        self._append_log("インストール完了。")
        self._skip_btn.setEnabled(True)
        ok_btn = QPushButton("完了")
        ok_btn.clicked.connect(self._finish)
        self._btn_box.addButton(ok_btn, QDialogButtonBox.ButtonRole.AcceptRole)

    # ------------------------------------------------------------------
    # 終了処理
    # ------------------------------------------------------------------

    def _on_skip_clicked(self) -> None:
        # キャンセル時も「次回表示しない」チェック状態を保存してから閉じる。
        self._config.set("SkipSetupWizard", self._dont_show_again_cb.isChecked())
        self.reject()

    def _finish(self) -> None:
        self._config.set("AutoUpdate", self._auto_update_cb.isChecked())
        self._config.set("SkipSetupWizard", self._dont_show_again_cb.isChecked())
        self.accept()

    def _append_log(self, text: str) -> None:
        self._log.append(text)
