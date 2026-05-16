#!/usr/bin/env bash
# Vytvoří AI Manager.app v /Applications
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_PATH="/Applications/AI Manager.app"
CONTENTS="$APP_PATH/Contents"

if [ ! -f "$HOME/ai-manager-venv/bin/python3" ]; then
  echo "❌  Virtualní prostředí nenalezeno. Spusť nejdřív ./install.sh"
  exit 1
fi

echo "==> Vytvářím $APP_PATH …"

# Struktura .app bundle
mkdir -p "$CONTENTS/MacOS"
mkdir -p "$CONTENTS/Resources"

# Launcher – stejná cesta jako start.sh (venv python3 → funguje)
cat > "$CONTENTS/MacOS/AI Manager" << SCRIPT
#!/bin/bash
PROJECT="$PROJECT_DIR"
PYTHON="\$HOME/ai-manager-venv/bin/python3"
if pgrep -f "ai-manager-venv.*main.py" > /dev/null 2>&1; then
    exit 0
fi
cd "\$PROJECT"
exec "\$PYTHON" main.py
SCRIPT
chmod +x "$CONTENTS/MacOS/AI Manager"

# Info.plist – LSUIElement = true → žádná ikona v Docku
cat > "$CONTENTS/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>             <string>AI Manager</string>
  <key>CFBundleDisplayName</key>      <string>AI Manager</string>
  <key>CFBundleIdentifier</key>       <string>com.benjaminpavelka.aimanager</string>
  <key>CFBundleVersion</key>          <string>$(grep VERSION "$PROJECT_DIR/version.py" | cut -d'"' -f2)</string>
  <key>CFBundleShortVersionString</key><string>$(grep VERSION "$PROJECT_DIR/version.py" | cut -d'"' -f2)</string>
  <key>CFBundleExecutable</key>       <string>AI Manager</string>
  <key>CFBundlePackageType</key>      <string>APPL</string>
  <key>LSUIElement</key>              <true/>
  <key>NSUserNotificationAlertStyle</key><string>alert</string>
  <key>NSHighResolutionCapable</key>  <true/>
</dict>
</plist>
PLIST

# Ikona (pokud existuje)
if [ -f "$PROJECT_DIR/resources/AppIcon.icns" ]; then
  cp "$PROJECT_DIR/resources/AppIcon.icns" "$CONTENTS/Resources/AppIcon.icns"
  /usr/libexec/PlistBuddy -c "Add :CFBundleIconFile string AppIcon" "$CONTENTS/Info.plist" 2>/dev/null || true
fi

# Odstranění macOS quarantine (jinak macOS blokuje spuštění)
xattr -dr com.apple.quarantine "$APP_PATH" 2>/dev/null || true

echo "✅  Hotovo: $APP_PATH"
echo ""
echo "Přidej do přihlašovacích položek:"
echo "  Nastavení → Obecné → Přihlašovací položky → +"
