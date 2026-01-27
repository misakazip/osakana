"""アプリケーション全体で使用するモダンなダークテーマ QSS スタイルシート。"""

STYLE = """
/* ── ベース ─────────────────────────────────────────────── */
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Noto Sans JP", sans-serif;
    font-size: 10pt;
}

/* ── ウィンドウ / ダイアログ ────────────────────────────────── */
QMainWindow, QDialog {
    background-color: #1e1e2e;
}

/* ── タブウィジェット ─────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #313244;
    border-radius: 6px;
    background-color: #1e1e2e;
}
QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    padding: 8px 20px;
    border: 1px solid #313244;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    min-width: 80px;
}
QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #cba6f7;
    border-bottom: 2px solid #cba6f7;
}
QTabBar::tab:hover:!selected {
    background-color: #313244;
    color: #cdd6f4;
}

/* ── ボタン ──────────────────────────────────────────────── */
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 5px 14px;
    min-height: 24px;
}
QPushButton:hover {
    background-color: #45475a;
    border-color: #cba6f7;
    color: #cba6f7;
}
QPushButton:pressed {
    background-color: #cba6f7;
    color: #1e1e2e;
}
QPushButton:disabled {
    background-color: #1e1e2e;
    color: #585b70;
    border-color: #313244;
}
QPushButton[primary="true"] {
    background-color: #cba6f7;
    color: #1e1e2e;
    border: none;
    font-weight: bold;
}
QPushButton[primary="true"]:hover {
    background-color: #d0b4fb;
}
QPushButton[primary="true"]:pressed {
    background-color: #b58df5;
}

/* ── 入力フィールド ──────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px 8px;
    selection-background-color: #cba6f7;
    selection-color: #1e1e2e;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #cba6f7;
}
QLineEdit:disabled {
    background-color: #1e1e2e;
    color: #585b70;
}

/* ── コンボボックス ──────────────────────────────────────── */
QComboBox {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 24px;
}
QComboBox:hover { border-color: #cba6f7; }
QComboBox:focus { border-color: #cba6f7; }
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox::down-arrow {
    width: 10px;
    height: 10px;
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    selection-background-color: #313244;
    selection-color: #cba6f7;
}

/* ── チェックボックス / ラジオボタン ─────────────────────── */
QCheckBox, QRadioButton {
    color: #cdd6f4;
    spacing: 8px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #45475a;
    border-radius: 3px;
    background-color: #181825;
}
QRadioButton::indicator { border-radius: 8px; }
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #cba6f7;
    border-color: #cba6f7;
}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {
    border-color: #cba6f7;
}

/* ── グループボックス ────────────────────────────────────── */
QGroupBox {
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: bold;
    color: #a6e3a1;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: #a6e3a1;
}
QGroupBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #45475a;
    border-radius: 3px;
    background-color: #181825;
}
QGroupBox::indicator:checked {
    background-color: #a6e3a1;
    border-color: #a6e3a1;
}

/* ── スライダー ──────────────────────────────────────────── */
QSlider::groove:horizontal {
    height: 4px;
    background-color: #313244;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background-color: #cba6f7;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background-color: #cba6f7;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background-color: #d0b4fb;
}

/* ── プログレスバー ──────────────────────────────────────── */
QProgressBar {
    background-color: #313244;
    border: none;
    border-radius: 4px;
    text-align: center;
    color: #cdd6f4;
    font-size: 9pt;
}
QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 4px;
}

/* ── スクロールバー ──────────────────────────────────────── */
QScrollBar:vertical {
    background-color: #181825;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background-color: #585b70; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background-color: #181825;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background-color: #45475a;
    border-radius: 5px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover { background-color: #585b70; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── テーブル ────────────────────────────────────────────── */
QTableWidget {
    background-color: #181825;
    color: #cdd6f4;
    gridline-color: #313244;
    border: 1px solid #313244;
    border-radius: 6px;
    alternate-background-color: #1e1e2e;
}
QTableWidget::item:selected {
    background-color: #313244;
    color: #cdd6f4;
}
QHeaderView::section {
    background-color: #181825;
    color: #a6adc8;
    border: none;
    border-bottom: 1px solid #313244;
    padding: 6px 8px;
    font-weight: bold;
}

/* ── ステータスバー ──────────────────────────────────────── */
QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
}

/* ── ラベル ──────────────────────────────────────────────── */
QLabel {
    color: #cdd6f4;
}

/* ── ツールチップ ────────────────────────────────────────── */
QToolTip {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
}

/* ── メッセージボックス ──────────────────────────────────── */
QMessageBox {
    background-color: #1e1e2e;
}
QMessageBox QLabel {
    color: #cdd6f4;
}
"""
