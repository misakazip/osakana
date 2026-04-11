# -*- mode: python ; coding: utf-8 -*-
#
# Osakana 用 PyInstaller spec ファイル。
#
# サイズ削減の方針:
#   1. 大きな / 未使用の Qt および stdlib モジュールを明示的に除外する。
#   2. 実際にインポートする Qt サブパッケージのみ収集する。
#   3. UPX 圧縮（UPX が PATH にある場合、pyinstaller が自動使用）。
#   4. デバッグシンボルを削除する（Linux / macOS で有効）。
#
# ライセンス方針:
#   PySide6 (LGPL-3.0) を使用し、Qt の共有ライブラリは PyInstaller によって
#   実行ファイルとは分離した動的ライブラリとしてバンドルされる。
#   これにより本体の MIT ライセンスと LGPL-3.0 が両立する。
#
import sys

# ── バンドルから除外するモジュール ───────────────────────────────
_EXCLUDE = [
    # PySide6 – 一切インポートしない大きなモジュール
    "PySide6.QtWebEngine",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtDesigner",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQml",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DExtras",
    "PySide6.QtSql",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtLocation",
    "PySide6.QtPositioning",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtStateMachine",
    "PySide6.QtNetworkAuth",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtDataVisualization",
    "PySide6.QtCharts",
    "PySide6.QtVirtualKeyboard",
    "PySide6.QtAxContainer",   # Windows COM（不要）
    "PyQt6",
    "PySide2",
    # stdlib – 安全に除外可能（PyInstaller のフックが依存しないもの）
    "tkinter",
    "_tkinter",
    "turtle",
    "unittest",
    "pydoc",
    "doctest",
    # distutils は PyInstaller 6.x の hook-distutils.py が内部で使うため除外不可
    "xmlrpc",
    "ftplib",
    "imaplib",
    "poplib",
    "smtplib",
    "mailbox",
    "curses",
    "readline",
    "test",
    "lib2to3",
    # asyncio / sqlite3 / multiprocessing / concurrent は
    # setuptools や urllib3 が間接的に参照するため除外しない
    "asyncore",
    "asynchat",
    "dbm",
    "dbm.dumb",
    "dbm.gnu",
    "dbm.ndbm",
    "ensurepip",
    "pdb",
    "bdb",
    "numpy",
    "pandas",
    "matplotlib",
    "PIL",
]

# ── 解析 ──────────────────────────────────────────────────────────
a = Analysis(
    ["src/main.py"],
    pathex=["src"],
    binaries=[],
    datas=[("LICENSE", ".")],
    hiddenimports=[
        # 使用するものだけを明示的に取り込む
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "shiboken6",
    ],
    hookspath=[],
    hooksconfig={
        # Qt フックを必要なプラグインのみに制限する
        "PySide6": {
            "qt_plugins": [
                "platforms",          # xcb (Linux), windows (Win), cocoa (macOS)
                "multimedia",         # 音声/動画バックエンド（Qt6 統合済み）
                "styles",             # macOS ネイティブスタイル
            ],
        },
    },
    runtime_hooks=[],
    excludes=_EXCLUDE,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="osakana",
    debug=False,
    bootloader_ignore_signals=False,
    # ELF / Mach-O デバッグシンボルを削除する — Linux / macOS で大幅なサイズ削減
    strip=(sys.platform != "win32"),
    # UPX 圧縮: macOS の Mach-O バイナリには UPX が非対応のため無効化
    upx=(sys.platform != "darwin"),
    upx_exclude=[
        # UPX が破損させる可能性のある DLL を除外
        "vcruntime140.dll",
        "python3*.dll",
        "Qt6Core.dll",
    ],
    runtime_tmpdir=None,
    # GUIアプリのためコンソール / コマンドウィンドウを表示しない
    console=False,
    disable_windowed_traceback=False,
    # macOS .app バンドルでのドラッグ＆ドロップ対応
    argv_emulation=(sys.platform == "darwin"),
    target_arch=None,
    # macOS コード署名（未署名の場合は None）
    codesign_identity=None,
    entitlements_file=None,
)
