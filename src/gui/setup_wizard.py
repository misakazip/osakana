"""初回起動 / バイナリ欠落時のセットアップウィザード。

フロー:
  1. 不足している必要バイナリを表示する。
  2. 手動インストールか自動インストールかを選択させる。
  3. （自動）各バイナリをプログレスバー付きでインストールする。
  4. yt-dlp の自動アップデートを有効にするか確認する。
  5. 閉じる。
"""
from __future__ import annotations

from typing import List

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QCheckBox,
)

from core.binary_manager import BinaryManager
from core.config import Config
from core.platform_detector import PlatformInfo


# ------------------------------------------------------------------
# バックグラウンドインストールワーカー
# ------------------------------------------------------------------

class _InstallWorker(QThread):
    progress     = pyqtSignal(str, int)   # バイナリ名, 0-100
    log_message  = pyqtSignal(str)
    finished_ok  = pyqtSignal(str, str)   # バイナリ名, パス
    finished_err = pyqtSignal(str, str)   # バイナリ名, エラー

    def __init__(
        self,
        name: str,
        manager: BinaryManager,
        parent: QWidget = None,
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


# ------------------------------------------------------------------
# ウィザードダイアログ
# ------------------------------------------------------------------

class SetupWizard(QDialog):
    def __init__(
        self,
        missing: List[str],
        manager: BinaryManager,
        config: Config,
        platform: PlatformInfo,
        parent: QWidget = None,
    ) -> None:
        super().__init__(parent)
        self._missing   = list(missing)
        self._manager   = manager
        self._config    = config
        self._platform  = platform
        self._workers: List[_InstallWorker] = []
        self._bars: dict[str, QProgressBar] = {}
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

        # ヘッダー
        title_lbl = QLabel("<b>必要なバイナリが見つかりません</b>")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        # 不足バイナリ一覧
        missing_text = "  •  " + "\n  •  ".join(self._missing)
        info_lbl = QLabel(f"以下のバイナリが見つかりませんでした:\n{missing_text}")
        info_lbl.setWordWrap(True)
        layout.addWidget(info_lbl)

        # インストールモード
        mode_box = QGroupBox("インストール方法")
        mode_layout = QVBoxLayout(mode_box)
        self._auto_rb   = QRadioButton("自動でインストールする（推奨）")
        self._manual_rb = QRadioButton("手動でインストールする（後で設定から確認）")
        self._auto_rb.setChecked(True)
        bg = QButtonGroup(self)
        bg.addButton(self._auto_rb)
        bg.addButton(self._manual_rb)
        mode_layout.addWidget(self._auto_rb)
        mode_layout.addWidget(self._manual_rb)
        layout.addWidget(mode_box)

        # 進捗エリア（インストール開始まで非表示）
        self._progress_group = QGroupBox("インストール進捗")
        prog_layout = QVBoxLayout(self._progress_group)
        for name in self._missing:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(f"{name}:")
            lbl.setFixedWidth(70)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            rl.addWidget(lbl)
            rl.addWidget(bar)
            prog_layout.addWidget(row)
            self._bars[name] = bar
        self._progress_group.setVisible(False)
        layout.addWidget(self._progress_group)

        # ログ
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(90)
        self._log.setVisible(False)
        layout.addWidget(self._log)

        # 自動アップデートオプション
        self._auto_update_cb = QCheckBox("yt-dlp の自動アップデートを有効にする")
        self._auto_update_cb.setChecked(False)
        layout.addWidget(self._auto_update_cb)

        # ボタン
        self._btn_box = QDialogButtonBox()
        self._install_btn = QPushButton("インストール開始")
        self._install_btn.setDefault(True)
        self._skip_btn = QPushButton("スキップして起動")
        self._btn_box.addButton(self._install_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        self._btn_box.addButton(self._skip_btn,    QDialogButtonBox.ButtonRole.RejectRole)
        self._install_btn.clicked.connect(self._on_install_clicked)
        self._skip_btn.clicked.connect(self._on_skip)
        layout.addWidget(self._btn_box)

        self._auto_rb.toggled.connect(self._on_mode_changed)

    # ------------------------------------------------------------------
    # スロット
    # ------------------------------------------------------------------

    def _on_mode_changed(self, auto: bool) -> None:
        self._install_btn.setEnabled(True)

    def _on_install_clicked(self) -> None:
        if self._manual_rb.isChecked():
            self._config.set("AutoInstall", False)
            self._finish()
            return

        # 自動インストール
        self._config.set("AutoInstall", True)
        self._install_btn.setEnabled(False)
        self._skip_btn.setEnabled(False)
        self._progress_group.setVisible(True)
        self._log.setVisible(True)
        self._pending = list(self._missing)
        self._install_next()

    def _install_next(self) -> None:
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
        if bar:
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

    def _on_skip(self) -> None:
        self.reject()

    def _finish(self) -> None:
        self._config.set("AutoUpdate", self._auto_update_cb.isChecked())
        self.accept()

    def _append_log(self, text: str) -> None:
        self._log.append(text)
