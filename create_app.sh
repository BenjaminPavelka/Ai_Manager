#!/usr/bin/env bash
# Vytvoří AI Manager.app v /Applications
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_PATH="/Applications/AI Manager.app"
CONTENTS="$APP_PATH/Contents"

# Framework Python je potřeba pro menu bar (CLI python3 menu bar nezobrazí)
FRAMEWORK_PYTHON="$(ls /opt/homebrew/Cellar/python@3.*/*/Frameworks/Python.framework/Versions/Current/Resources/Python.app/Contents/MacOS/Python 2>/dev/null | tail -1)"
if [ -z "$FRAMEWORK_PYTHON" ]; then
  echo "❌  Framework Python nenalezen. Nainstaluj Python přes Homebrew: brew install python"
  exit 1
fi

PY_VER="$("$FRAMEWORK_PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
SITE_PACKAGES="$HOME/ai-manager-venv/lib/python${PY_VER}/site-packages"

if [ ! -d "$SITE_PACKAGES/rumps" ]; then
  echo "❌  Virtualní prostředí nenalezeno. Spusť nejdřív:"
  echo "    python3 -m venv ~/ai-manager-venv"
  echo "    ~/ai-manager-venv/bin/pip install flask rumps pyobjc-framework-Cocoa"
  exit 1
fi

echo "==> Vytvářím $APP_PATH …"
echo "    Python:        $FRAMEWORK_PYTHON"
echo "    Site-packages: $SITE_PACKAGES"

# Struktura .app bundle
mkdir -p "$CONTENTS/MacOS"
mkdir -p "$CONTENTS/Resources"

# Launcher – musí používat Framework Python (ne CLI python3) pro zobrazení menu baru
cat > "$CONTENTS/MacOS/AI Manager" <<SCRIPT
#!/bin/bash
LOG="\$HOME/Library/Logs/AIManager.log"
mkdir -p "\$(dirname "\$LOG")"
echo "--- START \$(date) ---" >> "\$LOG"
export PYTHONPATH="$SITE_PACKAGES:$PROJECT_DIR"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd "$PROJECT_DIR"
exec "$FRAMEWORK_PYTHON" "$PROJECT_DIR/main.py" >> "\$LOG" 2>&1
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
