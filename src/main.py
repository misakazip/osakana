# Osakana — yt-dlp GUI クライアントのエントリーポイント。
from __future__ import annotations

import sys
from pathlib import Path

# 直接実行時 (開発環境) または PyInstaller 経由で起動した場合に
# ``src/`` を sys.path に追加してパッケージ解決を有効化する。
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication, QMessageBox

from core.binary_manager import BinaryManager
from core.config import Config
from core.platform_detector import PlatformInfo, detect as detect_platform
from core.updater import APP_VERSION, OsakanaUpdater, YtDlpUpdater
from gui.main_window import MainWindow
from gui.setup_wizard import SetupWizard
from gui.style import DARK_STYLE, LIGHT_STYLE


# ─────────────────────────────────────────────────────────────────────
# 起動前フェーズ: セットアップ / アップデート確認
# ─────────────────────────────────────────────────────────────────────

# 初回起動時にセットアップウィザードで案内するバイナリ一覧。
# yt-dlp / ffmpeg は必須、deno / aria2c は任意機能だが揃えて案内する。
_INSTALLABLE_AT_STARTUP = ["yt-dlp", "ffmpeg", "deno", "aria2c"]


def _ensure_required_binaries(
    binary_manager: BinaryManager,
    config: Config,
    platform_info: PlatformInfo,
) -> bool:
    # インストール対象バイナリのうち不足しているものがあればウィザードを表示する。
    # 続行してよい場合 True、ユーザがキャンセルした場合 False を返す。
    # ユーザが「次回表示しない」を選んでいればウィザードは一切開かない。
    if config.get("SkipSetupWizard"):
        return True

    missing = [n for n in _INSTALLABLE_AT_STARTUP if not binary_manager.find(n)]
    if not missing:
        return True

    wizard = SetupWizard(
        missing=missing,
        manager=binary_manager,
        config=config,
        platform=platform_info,
        parent=None,
    )
    return wizard.exec() == SetupWizard.DialogCode.Accepted


def _configure_aria2c(
    binary_manager: BinaryManager,
    config: Config,
    platform_info: PlatformInfo,
) -> None:
    # aria2c の検出結果を設定に反映し、必要ならインストールを促す。
    aria2c_path = binary_manager.find("aria2c")
    if aria2c_path:
        config.set("Aria2cPath", aria2c_path)
        return

    if config.get("IsAria2cEnabled"):
        # 有効設定なのに見つからない → インストールウィザードを表示
        SetupWizard(
            missing=["aria2c"],
            manager=binary_manager,
            config=config,
            platform=platform_info,
            parent=None,
        ).exec()


def _maybe_update_ytdlp(config: Config) -> None:
    # 自動アップデートが有効なら、確認ダイアログを出して更新する。
    ytdlp_path = config.get("YtdlpPath", "")
    if not (config.get("AutoUpdate") and ytdlp_path):
        return

    try:
        updater = YtDlpUpdater(ytdlp_path)
        if not updater.needs_update():
            return

        answer = QMessageBox.question(
            None,
            "yt-dlp アップデート",
            "yt-dlp の新しいバージョンが利用可能です。\n\n"
            f"現在のバージョン : {updater.current_version()}\n"
            f"最新バージョン   : {updater.latest_version()}\n\n"
            "今すぐ更新しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            updater.do_update()
    except Exception:
        pass  # アップデート確認の失敗は致命的エラーではない


def _maybe_update_app(config: Config) -> None:
    # Osakana 本体のアップデート確認を行い、案内ダイアログを表示する。
    if not config.get("AutoUpdateApp"):
        return

    try:
        updater = OsakanaUpdater()
        if not updater.needs_update():
            return

        QMessageBox.information(
            None,
            "Osakana アップデート",
            "Osakana の新しいバージョンが利用可能です。\n\n"
            f"現在のバージョン : {APP_VERSION}\n"
            f"最新バージョン   : {updater.latest_version()}\n\n"
            "リリースページからダウンロードしてください:\n"
            f"{updater.release_url()}",
        )
    except Exception:
        pass  # アップデート確認の失敗は致命的エラーではない


# ─────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────

def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Osakana")
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")

    config = Config()
    app.setStyleSheet(
        DARK_STYLE if config.get("IsDarkThemeEnabled", True) else LIGHT_STYLE
    )

    platform_info = detect_platform()
    binary_manager = BinaryManager(config, platform_info)

    if not _ensure_required_binaries(binary_manager, config, platform_info):
        sys.exit(0)

    _configure_aria2c(binary_manager, config, platform_info)
    _maybe_update_ytdlp(config)
    _maybe_update_app(config)

    window = MainWindow(config, binary_manager)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
