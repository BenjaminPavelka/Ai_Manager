#!/usr/bin/env bash
# Jednorázová instalace AI Manager na nový Mac
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$HOME/ai-manager-venv/bin/python3"
PLIST="$HOME/Library/LaunchAgents/com.benjaminpavelka.aimanager.plist"

echo "==> AI Manager – instalace"

# 1. Virtualní prostředí
if [ ! -f "$PYTHON" ]; then
  echo "  Vytvářím virtualní prostředí…"
  python3 -m venv "$HOME/ai-manager-venv"
  "$HOME/ai-manager-venv/bin/pip" install flask rumps pyobjc-framework-Cocoa -q
  echo "  ✓ Závislosti nainstalovány"
else
  echo "  ✓ Virtualní prostředí nalezeno"
fi

# 2. LaunchAgent
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.benjaminpavelka.aimanager</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$PROJECT_DIR/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>$HOME/Library/Logs/AIManager.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/Library/Logs/AIManager.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF

# 3. Načtení (spuštění)
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo ""
echo "✅  Hotovo! AI Manager běží v menu baru a spustí se automaticky po přihlášení."
echo ""
echo "Správa:"
echo "  Spustit:   launchctl load ~/Library/LaunchAgents/com.benjaminpavelka.aimanager.plist"
echo "  Zastavit:  launchctl unload ~/Library/LaunchAgents/com.benjaminpavelka.aimanager.plist"
echo "  Log:       tail -f ~/Library/Logs/AIManager.log"
