"""アプリケーションのメインウィンドウ。"""
from __future__ import annotations

from typing import Dict

from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QStyle,
    QSystemTrayIcon,
    QTabWidget,
)

from core.binary_manager import BinaryManager
from core.config import Config
from core.downloader import DownloadManager, DownloadTask
from gui.download_tab import DownloadTab
from gui.settings_tab import SettingsTab


class MainWindow(QMainWindow):
    def __init__(self, config: Config, binary_manager: BinaryManager) -> None:
        super().__init__()
        self._config = config
        self._bm = binary_manager
        self._task_titles: Dict[str, str] = {}
        self._setup_ui()
        self._setup_tray()

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
        self._dm.task_added.connect(self._on_task_added)
        self._dm.title_fetched.connect(self._on_title_fetched)
        self._dm.status_changed.connect(self._on_status_changed)

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self._tray: QSystemTrayIcon | None = None
            return
        icon = QApplication.windowIcon()
        if icon.isNull():
            # アプリアイコン未設定時のフォールバック。
            # Windows では null アイコンだとトレイに表示されず showMessage() も無効になる。
            icon = QApplication.style().standardIcon(
                QStyle.StandardPixmap.SP_ComputerIcon
            )
        self._tray = QSystemTrayIcon(icon, self)
        self._tray.show()

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

    def _on_task_added(self, task: DownloadTask) -> None:
        self._task_titles[task.id] = task.url[:80]

    def _on_title_fetched(self, task_id: str, title: str) -> None:
        if title:
            self._task_titles[task_id] = title

    def _on_status_changed(self, task_id: str, status: str) -> None:
        if status not in ("done", "failed"):
            return
        if self._tray is None or not self._config.get("DesktopNotify"):
            self._task_titles.pop(task_id, None)
            return
        display = self._task_titles.pop(task_id, "")
        if status == "done":
            self._tray.showMessage(
                "ダウンロード完了", display,
                QSystemTrayIcon.MessageIcon.Information, 4000,
            )
        else:
            self._tray.showMessage(
                "ダウンロード失敗", display,
                QSystemTrayIcon.MessageIcon.Warning, 4000,
            )
