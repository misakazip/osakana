"""アプリケーションのメインウィンドウ。"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QLabel,
    QMainWindow,
    QTabWidget,
    QWidget,
)

from core.binary_manager import BinaryManager
from core.config import Config
from core.downloader import DownloadManager
from gui.download_tab import DownloadTab
from gui.settings_tab import SettingsTab


class MainWindow(QMainWindow):
    def __init__(self, config: Config, binary_manager: BinaryManager) -> None:
        super().__init__()
        self._config = config
        self._bm = binary_manager
        self._setup_ui()

    # ------------------------------------------------------------------
    # セットアップ
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setWindowTitle("Osakana — yt-dlp GUI")
        self.resize(960, 660)

        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)

        # 共有ダウンロードマネージャ（ウィンドウと同じライフタイム）
        self._dm = DownloadManager(self._config, parent=self)

        self._dl_tab = DownloadTab(self._dm, self._config)
        self._st_tab = SettingsTab(self._config, self._bm)

        self._tabs.addTab(self._dl_tab, "ダウンロード")
        self._tabs.addTab(self._st_tab, "設定")

        # ステータスバー
        self._status_lbl = QLabel("準備完了")
        self.statusBar().addPermanentWidget(self._status_lbl)

        self._dm.queue_stats.connect(self._update_status)

    # ------------------------------------------------------------------
    # スロット
    # ------------------------------------------------------------------

    def _update_status(self, active: int, queued: int) -> None:
        if active == 0 and queued == 0:
            self._status_lbl.setText("待機中")
        else:
            self._status_lbl.setText(
                f"ダウンロード中: {active} 件  /  待機: {queued} 件"
            )
