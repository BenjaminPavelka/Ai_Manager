#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
  echo "📦 Vytvářím virtuální prostředí..."
  python3 -m venv .venv
fi

source .venv/bin/activate

# Install/update dependencies
pip install -q -r requirements.txt

echo "🚀 Spouštím AI Manager..."
python app.py
