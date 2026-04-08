# アプリケーション全体で使用する QSS スタイルシート。
#
# ダーク (Catppuccin Mocha) とライト (Catppuccin Latte) の 2 種類を提供する。
# 両テーマは同じ構造の QSS テンプレートに Palette を当てはめて生成するため、
# 配色を変更したい場合はパレット定義のみを編集すればよい。
from __future__ import annotations

from dataclasses import dataclass


# ─────────────────────────────────────────────────────────────────────
# パレット定義
# ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Palette:
    # テーマカラーの集合。Catppuccin の命名規則に準ずる。

    base: str            # ウィンドウ / ダイアログ背景
    mantle: str          # 入力欄など 1 段沈んだ背景
    surface0: str        # ボタン背景・罫線・代替行
    surface1: str        # ボタン罫線・hover・スクロール
    surface2: str        # disabled テキスト・スクロール hover
    text: str            # 主テキスト
    subtext: str         # 補助テキスト
    accent: str          # 強調色 (フォーカス・選択・タブ)
    accent_hover: str    # 強調色 hover
    accent_pressed: str  # 強調色 pressed
    group: str           # GroupBox タイトル / インジケータ
    progress: str        # プログレスバー chunk


# Catppuccin Mocha (ダーク)
_MOCHA = Palette(
    base="#1e1e2e",
    mantle="#181825",
    surface0="#313244",
    surface1="#45475a",
    surface2="#585b70",
    text="#cdd6f4",
    subtext="#a6adc8",
    accent="#cba6f7",
    accent_hover="#d0b4fb",
    accent_pressed="#b58df5",
    group="#a6e3a1",
    progress="#89b4fa",
)

# Catppuccin Latte (ライト)
_LATTE = Palette(
    base="#eff1f5",
    mantle="#e6e9ef",
    surface0="#ccd0da",
    surface1="#bcc0cc",
    surface2="#acb0be",
    text="#4c4f69",
    subtext="#6c6f85",
    accent="#8839ef",
    accent_hover="#7527d7",
    accent_pressed="#6516bf",
    group="#40a02b",
    progress="#1e66f5",
)


# ─────────────────────────────────────────────────────────────────────
# QSS テンプレート
# ─────────────────────────────────────────────────────────────────────

def _render(p: Palette) -> str:
    # パレットを QSS テンプレートに当てはめて文字列を生成する。
    return f"""
/* ── ベース ─────────────────────────────────────────────── */
QWidget {{
    background-color: {p.base};
    color: {p.text};
    font-family: "Segoe UI", "Noto Sans JP", sans-serif;
    font-size: 10pt;
}}

/* ── ウィンドウ / ダイアログ ────────────────────────────────── */
QMainWindow, QDialog {{
    background-color: {p.base};
}}

/* ── タブウィジェット ─────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {p.surface0};
    border-radius: 6px;
    background-color: {p.base};
}}
QTabBar::tab {{
    background-color: {p.mantle};
    color: {p.subtext};
    padding: 8px 20px;
    border: 1px solid {p.surface0};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    min-width: 80px;
}}
QTabBar::tab:selected {{
    background-color: {p.base};
    color: {p.accent};
    border-bottom: 2px solid {p.accent};
}}
QTabBar::tab:hover:!selected {{
    background-color: {p.surface0};
    color: {p.text};
}}

/* ── ボタン ──────────────────────────────────────────────── */
QPushButton {{
    background-color: {p.surface0};
    color: {p.text};
    border: 1px solid {p.surface1};
    border-radius: 6px;
    padding: 5px 14px;
    min-height: 24px;
}}
QPushButton:hover {{
    background-color: {p.surface1};
    border-color: {p.accent};
    color: {p.accent};
}}
QPushButton:pressed {{
    background-color: {p.accent};
    color: {p.base};
}}
QPushButton:disabled {{
    background-color: {p.base};
    color: {p.surface2};
    border-color: {p.surface0};
}}
QPushButton[primary="true"] {{
    background-color: {p.accent};
    color: {p.base};
    border: none;
    font-weight: bold;
}}
QPushButton[primary="true"]:hover {{
    background-color: {p.accent_hover};
}}
QPushButton[primary="true"]:pressed {{
    background-color: {p.accent_pressed};
}}

/* ── テーマ切替ボタン ────────────────────────────────────── */
QPushButton[theme-toggle="true"] {{
    background-color: transparent;
    border: none;
    font-size: 16pt;
    padding: 0px 4px;
    min-height: 0;
    min-width: 0;
}}
QPushButton[theme-toggle="true"]:hover {{
    background-color: {p.surface0};
    border: none;
    color: {p.text};
}}
QPushButton[theme-toggle="true"]:pressed {{
    background-color: {p.surface1};
}}

/* ── 入力フィールド ──────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {p.mantle};
    color: {p.text};
    border: 1px solid {p.surface1};
    border-radius: 6px;
    padding: 4px 8px;
    selection-background-color: {p.accent};
    selection-color: {p.base};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {p.accent};
}}
QLineEdit:disabled {{
    background-color: {p.base};
    color: {p.surface2};
}}

/* ── コンボボックス ──────────────────────────────────────── */
QComboBox {{
    background-color: {p.mantle};
    color: {p.text};
    border: 1px solid {p.surface1};
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 24px;
}}
QComboBox:hover {{ border-color: {p.accent}; }}
QComboBox:focus {{ border-color: {p.accent}; }}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox::down-arrow {{
    width: 10px;
    height: 10px;
    border: none;
}}
QComboBox QAbstractItemView {{
    background-color: {p.mantle};
    color: {p.text};
    border: 1px solid {p.surface1};
    border-radius: 4px;
    selection-background-color: {p.surface0};
    selection-color: {p.accent};
}}

/* ── チェックボックス / ラジオボタン ─────────────────────── */
QCheckBox, QRadioButton {{
    color: {p.text};
    spacing: 8px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {p.surface1};
    border-radius: 3px;
    background-color: {p.mantle};
}}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {p.accent};
    border-color: {p.accent};
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {p.accent};
}}

/* ── グループボックス ────────────────────────────────────── */
QGroupBox {{
    border: 1px solid {p.surface0};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: bold;
    color: {p.group};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: {p.group};
}}
QGroupBox::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {p.surface1};
    border-radius: 3px;
    background-color: {p.mantle};
}}
QGroupBox::indicator:checked {{
    background-color: {p.group};
    border-color: {p.group};
}}

/* ── スライダー ──────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 4px;
    background-color: {p.surface0};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background-color: {p.accent};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background-color: {p.accent};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background-color: {p.accent_hover};
}}

/* ── プログレスバー ──────────────────────────────────────── */
QProgressBar {{
    background-color: {p.surface0};
    border: none;
    border-radius: 4px;
    text-align: center;
    color: {p.text};
    font-size: 9pt;
}}
QProgressBar::chunk {{
    background-color: {p.progress};
    border-radius: 4px;
}}

/* ── スクロールバー ──────────────────────────────────────── */
QScrollBar:vertical {{
    background-color: {p.mantle};
    width: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background-color: {p.surface1};
    border-radius: 5px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{ background-color: {p.surface2}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background-color: {p.mantle};
    height: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background-color: {p.surface1};
    border-radius: 5px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{ background-color: {p.surface2}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── テーブル ────────────────────────────────────────────── */
QTableWidget {{
    background-color: {p.mantle};
    color: {p.text};
    gridline-color: {p.surface0};
    border: 1px solid {p.surface0};
    border-radius: 6px;
    alternate-background-color: {p.base};
}}
QTableWidget::item:selected {{
    background-color: {p.surface0};
    color: {p.text};
}}
QHeaderView::section {{
    background-color: {p.mantle};
    color: {p.subtext};
    border: none;
    border-bottom: 1px solid {p.surface0};
    padding: 6px 8px;
    font-weight: bold;
}}

/* ── ステータスバー ──────────────────────────────────────── */
QStatusBar {{
    background-color: {p.mantle};
    color: {p.subtext};
    border-top: 1px solid {p.surface0};
}}

/* ── ラベル ──────────────────────────────────────────────── */
QLabel {{
    color: {p.text};
}}

/* ── ツールチップ ────────────────────────────────────────── */
QToolTip {{
    background-color: {p.surface0};
    color: {p.text};
    border: 1px solid {p.surface1};
    border-radius: 4px;
    padding: 4px 8px;
}}

/* ── メッセージボックス ──────────────────────────────────── */
QMessageBox {{
    background-color: {p.base};
}}
QMessageBox QLabel {{
    color: {p.text};
}}
"""


# ─────────────────────────────────────────────────────────────────────
# 公開定数
# ─────────────────────────────────────────────────────────────────────

DARK_STYLE = _render(_MOCHA)
LIGHT_STYLE = _render(_LATTE)

# 後方互換エイリアス
STYLE = DARK_STYLE
