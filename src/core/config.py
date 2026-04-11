# ~/.osakana/config の読み書きを行う。
#
# ファイル形式 (1 行 1 エントリ):
#
#     # コメント行
#     Key: value
#
# 真偽値は "true" / "false"、数値はそのまま整数として保存される。
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .platform_detector import detect as detect_platform

# ─────────────────────────────────────────────────────────────────────
# 定数
# ─────────────────────────────────────────────────────────────────────

CONFIG_DIR = Path.home() / ".osakana"
CONFIG_PATH = CONFIG_DIR / "config"
# 旧バージョンの設定ファイルパス。存在すれば新パスへ一度だけ移行する。
_LEGACY_CONFIG_PATH = Path.home() / ".osakana_config"

# 設定項目のデフォルト値。UI 上のグループごとに並べてある。
DEFAULTS: Dict[str, Any] = {
    # ── インストール / アップデート ────────────────────────
    "AutoInstall":          False,
    "AutoUpdate":           False,
    "AutoUpdateApp":        False,
    "SkipSetupWizard":      False,   # キャンセル時に「次回表示しない」を選ぶと True

    # ── aria2c ──────────────────────────────────────────────
    "IsAria2cEnabled":      False,
    "Aria2cConnections":    16,
    "MaxParallelDownloads": 2,

    # ── 出力 ────────────────────────────────────────────────
    "OutputDirectory":      str(Path.home() / "Downloads"),
    "FilenameTemplate":     "%(title)s [%(id)s].%(ext)s",

    # ── ダウンロード制御 ────────────────────────────────────
    "SpeedLimit":           "",
    "Retries":              10,
    "DownloadArchive":      "",

    # ── 字幕 ────────────────────────────────────────────────
    "SubLangs":             "ja,en",
    "AutoSubs":             False,
    "SubFormat":            "srt",

    # ── 後処理 ──────────────────────────────────────────────
    "EmbedThumbnail":       False,
    "EmbedMetadata":        False,
    "SponsorBlock":         "off",
    "HwAccel":              "none",

    # ── ネットワーク ────────────────────────────────────────
    "Proxy":                "",
    "CookiesBrowser":       "",

    # ── 通知 / 外観 ─────────────────────────────────────────
    "DesktopNotify":        False,
    "IsDarkThemeEnabled":   False,

    # ── バイナリパス ────────────────────────────────────────
    "YtdlpPath":            "",
    "FfmpegPath":           "",
    "DenoPath":             "",
    "Aria2cPath":           "",

    # ── その他 ──────────────────────────────────────────────
    "ExtraArgs":            "",
}


# ─────────────────────────────────────────────────────────────────────
# シリアライズ
# ─────────────────────────────────────────────────────────────────────

def _serialize(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _deserialize(raw: str) -> Any:
    # 文字列を適切な Python 型に変換する (bool / int / str)。
    text = raw.strip()
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return int(text)
    except ValueError:
        return text


# ─────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────

class Config:
    # 設定ファイルへの読み書きファサード。書き込みの度にファイル全体を再生成する。

    def __init__(self) -> None:
        self._data: Dict[str, Any] = DEFAULTS.copy()
        self._platform = detect_platform()

        # 旧パス (~/.osakana_config) があれば新パスへ移行する。
        if not CONFIG_PATH.exists() and _LEGACY_CONFIG_PATH.exists():
            try:
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                _LEGACY_CONFIG_PATH.replace(CONFIG_PATH)
            except OSError:
                pass

        if CONFIG_PATH.exists():
            self._load()
        else:
            self.save()

    # ------------------------------------------------------------------
    # 公開API
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        # 単一項目を更新し即座に保存する。
        self._data[key] = value
        self.save()

    def update(self, updates: Dict[str, Any]) -> None:
        # 複数項目を一括更新し 1 回だけ保存する。
        self._data.update(updates)
        self.save()

    def save(self) -> None:
        # 現在の設定値をディスクへ書き出す。
        header_lines = [
            "# Osakana Config",
            f"# Platform: {self._platform.display_name}",
            f"# Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]
        body_lines = [f"{key}: {_serialize(value)}" for key, value in self._data.items()]
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            "\n".join(header_lines + body_lines) + "\n",
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # 読み込み
    # ------------------------------------------------------------------

    def _load(self) -> None:
        # ファイルから設定を読み込む。未知キーは無視する。
        with CONFIG_PATH.open("r", encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                key, _, value = line.partition(":")
                key = key.strip()
                if key in DEFAULTS:
                    self._data[key] = _deserialize(value)
