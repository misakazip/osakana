#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 依存パッケージのインストール
pip install -r requirements.txt pyinstaller

# ビルド
pyinstaller osakana.spec

# バイナリをスクリプトのディレクトリにコピー
if [[ "${OSTYPE}" == "msys" || "${OSTYPE}" == "cygwin" || "${OS:-}" == "Windows_NT" ]]; then
    cp dist/osakana.exe ./osakana.exe
    echo "Built: ${SCRIPT_DIR}/osakana.exe"
else
    cp dist/osakana ./osakana
    echo "Built: ${SCRIPT_DIR}/osakana"
fi
