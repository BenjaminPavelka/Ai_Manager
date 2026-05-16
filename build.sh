#!/usr/bin/env bash
set -euo pipefail

echo "==> Instaluji závislosti…"
pip install -r requirements.txt py2app

echo "==> Čistím předchozí build…"
rm -rf build dist

echo "==> Stavím .app bundle…"
python setup.py py2app

echo ""
echo "✅  Hotovo! Aplikace je v dist/AI Manager.app"
echo "    Přetáhni ji do složky /Applications nebo ji rovnou spusť:"
echo "    open 'dist/AI Manager.app'"
