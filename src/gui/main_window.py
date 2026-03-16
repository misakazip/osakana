"""アプリケーションのメインウィンドウ。"""
from __future__ import annotations

from typing import Dict, cast

from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QStyle,
    QSystemTrayIcon,
    QTabWidget,
)

from core.binary_manager import BinaryManager
from core.config import Config
from core.downloader import DownloadManager, DownloadTask
from gui.download_tab import DownloadTab
from gui.settings_tab import SettingsTab
from gui.style import DARK_STYLE, LIGHT_STYLE


class MainWindow(QMainWindow):
    def __init__(self, config: Config, binary_manager: BinaryManager) -> None:
        super().__init__()
        self._config = config
        self._bm = binary_manager
        self._task_titles: Dict[str, str] = {}
        self._stats_total: int = 0
        self._stats_done: int = 0
        self._setup_ui()
        self._setup_tray()

    # ------------------------------------------------------------------
    # セットアップ
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setWindowTitle("Osakana — yt-dlp GUI")
        self.resize(960, 660)
        self.setMinimumSize(640, 480)

        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)

        # 共有ダウンロードマネージャ（ウィンドウと同じライフタイム）
        self._dm = DownloadManager(self._config, parent=self)

        self._dl_tab = DownloadTab(self._dm, self._config)
        self._st_tab = SettingsTab(self._config, self._bm)

        self._tabs.addTab(self._dl_tab, "ダウンロード")
        self._tabs.addTab(self._st_tab, "設定")

        # ステータスバー
        status_bar = self.statusBar()
        assert status_bar is not None
        self._status_lbl = QLabel("準備完了")
        status_bar.addPermanentWidget(self._status_lbl)

        # テーマ切替ボタン（右端: ダーク→🌙 / ライト→☀）
        self._theme_btn = QPushButton()
        self._theme_btn.setProperty("theme-toggle", True)
        self._theme_btn.setToolTip("ライト / ダークモード切替")
        self._theme_btn.setFlat(True)
        self._update_theme_button()
        self._theme_btn.clicked.connect(self._toggle_theme)
        status_bar.addPermanentWidget(self._theme_btn)

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
            style = QApplication.style()
            if style is not None:
                icon = style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self._tray = QSystemTrayIcon(icon, self)
        self._tray.show()

    # ------------------------------------------------------------------
    # テーマ
    # ------------------------------------------------------------------

    def _update_theme_button(self) -> None:
        is_dark = self._config.get("IsDarkThemeEnabled", True)
        self._theme_btn.setText("🌙" if is_dark else "☀")

    def _toggle_theme(self) -> None:
        is_dark = not self._config.get("IsDarkThemeEnabled", True)
        self._config.set("IsDarkThemeEnabled", is_dark)
        stylesheet = DARK_STYLE if is_dark else LIGHT_STYLE
        cast(QApplication, QApplication.instance()).setStyleSheet(stylesheet)
        self._update_theme_button()

    # ------------------------------------------------------------------
    # スロット
    # ------------------------------------------------------------------

    def _update_status(self, active: int, queued: int) -> None:
        if active == 0 and queued == 0 and self._stats_total == 0:
            self._status_lbl.setText("待機中")
        elif active == 0 and queued == 0:
            self._status_lbl.setText(
                f"完了: {self._stats_done} / {self._stats_total} 件"
            )
        else:
            self._status_lbl.setText(
                f"ダウンロード中: {active} 件  /  待機: {queued} 件"
                f"  ({self._stats_done} / {self._stats_total} 完了)"
            )

    def _on_task_added(self, task: DownloadTask) -> None:
        self._task_titles[task.id] = task.url[:80]
        self._stats_total += 1

    def _on_title_fetched(self, task_id: str, title: str) -> None:
        if title:
            self._task_titles[task_id] = title

    def _on_status_changed(self, task_id: str, status: str) -> None:
        if status not in ("done", "failed", "cancelled"):
            return
        self._stats_done += 1
        display = self._task_titles.pop(task_id, "")
        if status == "cancelled" or self._tray is None or not self._config.get("DesktopNotify"):
            return
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
