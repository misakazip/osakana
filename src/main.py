"""Osakana — yt-dlp GUIクライアントのエントリーポイント。"""
from __future__ import annotations

import sys
from pathlib import Path

# 直接実行時（開発環境）またはPyInstaller経由で実行する場合、src/ を sys.path に追加する
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication, QMessageBox

from core.binary_manager import BinaryManager
from core.config import Config
from core.platform_detector import detect as detect_platform
from core.updater import YtDlpUpdater
from gui.main_window import MainWindow
from gui.setup_wizard import SetupWizard
from gui.style import DARK_STYLE, LIGHT_STYLE


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Osakana")
    app.setApplicationVersion("1.0.0")
    app.setStyle("Fusion")

    config = Config()
    stylesheet = DARK_STYLE if config.get("IsDarkThemeEnabled", True) else LIGHT_STYLE
    app.setStyleSheet(stylesheet)
    platform_info = detect_platform()
    binary_manager = BinaryManager(config, platform_info)

    # ----------------------------------------------------------------
    # バイナリ確認: 必要なバイナリが欠けている場合はセットアップウィザードを表示
    # ----------------------------------------------------------------
    missing = binary_manager.get_missing()
    if missing:
        wizard = SetupWizard(
            missing=missing,
            manager=binary_manager,
            config=config,
            platform=platform_info,
            parent=None,
        )
        if wizard.exec() != SetupWizard.DialogCode.Accepted:
            sys.exit(0)

    # ----------------------------------------------------------------
    # aria2c の自動検索とconfigへの保存
    # ----------------------------------------------------------------
    aria2c_path = binary_manager.find("aria2c")
    if aria2c_path:
        config.set("Aria2cPath", aria2c_path)
    elif config.get("IsAria2cEnabled"):
        # aria2c が有効設定なのに見つからない場合はインストールを促す
        wizard = SetupWizard(
            missing=["aria2c"],
            manager=binary_manager,
            config=config,
            platform=platform_info,
            parent=None,
        )
        wizard.exec()

    # ----------------------------------------------------------------
    # 自動アップデート確認（インタラクティブ）
    # ----------------------------------------------------------------
    ytdlp_path = config.get("YtdlpPath", "")
    if config.get("AutoUpdate") and ytdlp_path:
        try:
            updater = YtDlpUpdater(ytdlp_path)
            if updater.needs_update():
                current = updater.current_version()
                latest  = updater.latest_version()
                answer = QMessageBox.question(
                    None,
                    "yt-dlp アップデート",
                    f"yt-dlp の新しいバージョンが利用可能です。\n\n"
                    f"現在のバージョン : {current}\n"
                    f"最新バージョン   : {latest}\n\n"
                    "今すぐ更新しますか？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if answer == QMessageBox.StandardButton.Yes:
                    updater.do_update()
        except Exception:
            pass  # アップデート確認の失敗は致命的エラーではない

    # ----------------------------------------------------------------
    # メインウィンドウを起動
    # ----------------------------------------------------------------
    window = MainWindow(config, binary_manager)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
