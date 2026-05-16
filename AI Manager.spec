# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec pro AI Manager

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

hidden_imports = [
    *collect_submodules("flask"),
    *collect_submodules("jinja2"),
    *collect_submodules("werkzeug"),
    *collect_submodules("rumps"),
    "objc",
    "AppKit",
    "Foundation",
    "Cocoa",
    "CoreFoundation",
    "LaunchServices",
    "UserNotifications",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("templates", "templates"),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AI Manager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="AI Manager",
)

app = BUNDLE(
    coll,
    name="AI Manager.app",
    icon="resources/AppIcon.icns" if __import__("os").path.exists("resources/AppIcon.icns") else None,
    bundle_identifier="com.benjaminpavelka.aimanager",
    info_plist={
        "CFBundleName": "AI Manager",
        "CFBundleDisplayName": "AI Manager",
        "CFBundleShortVersionString": open("version.py").read().split('"')[1],
        "CFBundleVersion": open("version.py").read().split('"')[1],
        "LSUIElement": True,
        "NSUserNotificationAlertStyle": "alert",
        "NSHighResolutionCapable": True,
        "NSAppleEventsUsageDescription": "AI Manager potřebuje přístup k systémovým událostem.",
    },
)
