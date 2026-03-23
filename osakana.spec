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
import sys

# ── バンドルから除外するモジュール ───────────────────────────────
_EXCLUDE = [
    # Qt – 一切インポートしない大きなモジュール
    "PyQt6.QtWebEngine",
    "PyQt6.QtWebEngineCore",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebEngineQuick",
    "PyQt6.QtDesigner",
    "PyQt6.QtQuick",
    "PyQt6.QtQuickWidgets",
    "PyQt6.QtQml",
    "PyQt6.Qt3DCore",
    "PyQt6.Qt3DInput",
    "PyQt6.Qt3DLogic",
    "PyQt6.Qt3DRender",
    "PyQt6.Qt3DAnimation",
    "PyQt6.Qt3DExtras",
    "PyQt6.QtSql",
    "PyQt6.QtBluetooth",
    "PyQt6.QtNfc",
    "PyQt6.QtLocation",
    "PyQt6.QtPositioning",
    "PyQt6.QtSensors",
    "PyQt6.QtSerialPort",
    "PyQt6.QtRemoteObjects",
    "PyQt6.QtScxml",
    "PyQt6.QtStateMachine",
    "PyQt6.QtNetworkAuth",
    "PyQt6.QtOpenGL",
    "PyQt6.QtOpenGLWidgets",
    "PyQt6.QtPdf",
    "PyQt6.QtPdfWidgets",
    "PyQt6.QtDataVisualization",
    "PyQt6.QtCharts",
    "PyQt6.QtVirtualKeyboard",
    "PyQt6.QtAxContainer",   # Windows COM（不要）
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
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.QtMultimedia",
        "PyQt6.QtMultimediaWidgets",
        "PyQt6.sip",
    ],
    hookspath=[],
    hooksconfig={
        # Qt フックを必要なプラグインのみに制限する
        "PyQt6": {
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
