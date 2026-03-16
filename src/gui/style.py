"""アプリケーション全体で使用する QSS スタイルシート（ダーク / ライト）。"""

# ── Catppuccin Mocha（ダーク） ────────────────────────────────────────────
DARK_STYLE = """
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

/* ── テーマ切替ボタン ────────────────────────────────────── */
QPushButton[theme-toggle="true"] {
    background-color: transparent;
    border: none;
    font-size: 16pt;
    padding: 0px 4px;
    min-height: 0;
    min-width: 0;
}
QPushButton[theme-toggle="true"]:hover {
    background-color: #313244;
    border: none;
    color: #cdd6f4;
}
QPushButton[theme-toggle="true"]:pressed {
    background-color: #45475a;
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

# ── Catppuccin Latte（ライト） ────────────────────────────────────────────
LIGHT_STYLE = """
/* ── ベース ─────────────────────────────────────────────── */
QWidget {
    background-color: #eff1f5;
    color: #4c4f69;
    font-family: "Segoe UI", "Noto Sans JP", sans-serif;
    font-size: 10pt;
}

/* ── ウィンドウ / ダイアログ ────────────────────────────────── */
QMainWindow, QDialog {
    background-color: #eff1f5;
}

/* ── タブウィジェット ─────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #ccd0da;
    border-radius: 6px;
    background-color: #eff1f5;
}
QTabBar::tab {
    background-color: #e6e9ef;
    color: #6c6f85;
    padding: 8px 20px;
    border: 1px solid #ccd0da;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    min-width: 80px;
}
QTabBar::tab:selected {
    background-color: #eff1f5;
    color: #8839ef;
    border-bottom: 2px solid #8839ef;
}
QTabBar::tab:hover:!selected {
    background-color: #ccd0da;
    color: #4c4f69;
}

/* ── ボタン ──────────────────────────────────────────────── */
QPushButton {
    background-color: #ccd0da;
    color: #4c4f69;
    border: 1px solid #bcc0cc;
    border-radius: 6px;
    padding: 5px 14px;
    min-height: 24px;
}
QPushButton:hover {
    background-color: #bcc0cc;
    border-color: #8839ef;
    color: #8839ef;
}
QPushButton:pressed {
    background-color: #8839ef;
    color: #eff1f5;
}
QPushButton:disabled {
    background-color: #eff1f5;
    color: #acb0be;
    border-color: #ccd0da;
}
QPushButton[primary="true"] {
    background-color: #8839ef;
    color: #eff1f5;
    border: none;
    font-weight: bold;
}
QPushButton[primary="true"]:hover {
    background-color: #7527d7;
}
QPushButton[primary="true"]:pressed {
    background-color: #6516bf;
}

/* ── テーマ切替ボタン ────────────────────────────────────── */
QPushButton[theme-toggle="true"] {
    background-color: transparent;
    border: none;
    font-size: 16pt;
    padding: 0px 4px;
    min-height: 0;
    min-width: 0;
}
QPushButton[theme-toggle="true"]:hover {
    background-color: #ccd0da;
    border: none;
    color: #4c4f69;
}
QPushButton[theme-toggle="true"]:pressed {
    background-color: #bcc0cc;
}

/* ── 入力フィールド ──────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {
    background-color: #e6e9ef;
    color: #4c4f69;
    border: 1px solid #bcc0cc;
    border-radius: 6px;
    padding: 4px 8px;
    selection-background-color: #8839ef;
    selection-color: #eff1f5;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #8839ef;
}
QLineEdit:disabled {
    background-color: #eff1f5;
    color: #acb0be;
}

/* ── コンボボックス ──────────────────────────────────────── */
QComboBox {
    background-color: #e6e9ef;
    color: #4c4f69;
    border: 1px solid #bcc0cc;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 24px;
}
QComboBox:hover { border-color: #8839ef; }
QComboBox:focus { border-color: #8839ef; }
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
    background-color: #e6e9ef;
    color: #4c4f69;
    border: 1px solid #bcc0cc;
    border-radius: 4px;
    selection-background-color: #ccd0da;
    selection-color: #8839ef;
}

/* ── チェックボックス / ラジオボタン ─────────────────────── */
QCheckBox, QRadioButton {
    color: #4c4f69;
    spacing: 8px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #bcc0cc;
    border-radius: 3px;
    background-color: #e6e9ef;
}
QRadioButton::indicator { border-radius: 8px; }
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #8839ef;
    border-color: #8839ef;
}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {
    border-color: #8839ef;
}

/* ── グループボックス ────────────────────────────────────── */
QGroupBox {
    border: 1px solid #ccd0da;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: bold;
    color: #40a02b;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: #40a02b;
}
QGroupBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #bcc0cc;
    border-radius: 3px;
    background-color: #e6e9ef;
}
QGroupBox::indicator:checked {
    background-color: #40a02b;
    border-color: #40a02b;
}

/* ── スライダー ──────────────────────────────────────────── */
QSlider::groove:horizontal {
    height: 4px;
    background-color: #ccd0da;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background-color: #8839ef;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background-color: #8839ef;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background-color: #7527d7;
}

/* ── プログレスバー ──────────────────────────────────────── */
QProgressBar {
    background-color: #ccd0da;
    border: none;
    border-radius: 4px;
    text-align: center;
    color: #4c4f69;
    font-size: 9pt;
}
QProgressBar::chunk {
    background-color: #1e66f5;
    border-radius: 4px;
}

/* ── スクロールバー ──────────────────────────────────────── */
QScrollBar:vertical {
    background-color: #e6e9ef;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background-color: #bcc0cc;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background-color: #acb0be; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background-color: #e6e9ef;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background-color: #bcc0cc;
    border-radius: 5px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover { background-color: #acb0be; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── テーブル ────────────────────────────────────────────── */
QTableWidget {
    background-color: #e6e9ef;
    color: #4c4f69;
    gridline-color: #ccd0da;
    border: 1px solid #ccd0da;
    border-radius: 6px;
    alternate-background-color: #eff1f5;
}
QTableWidget::item:selected {
    background-color: #ccd0da;
    color: #4c4f69;
}
QHeaderView::section {
    background-color: #e6e9ef;
    color: #6c6f85;
    border: none;
    border-bottom: 1px solid #ccd0da;
    padding: 6px 8px;
    font-weight: bold;
}

/* ── ステータスバー ──────────────────────────────────────── */
QStatusBar {
    background-color: #e6e9ef;
    color: #6c6f85;
    border-top: 1px solid #ccd0da;
}

/* ── ラベル ──────────────────────────────────────────────── */
QLabel {
    color: #4c4f69;
}

/* ── ツールチップ ────────────────────────────────────────── */
QToolTip {
    background-color: #ccd0da;
    color: #4c4f69;
    border: 1px solid #bcc0cc;
    border-radius: 4px;
    padding: 4px 8px;
}

/* ── メッセージボックス ──────────────────────────────────── */
QMessageBox {
    background-color: #eff1f5;
}
QMessageBox QLabel {
    color: #4c4f69;
}
"""

# 後方互換エイリアス
STYLE = DARK_STYLE
