"""
py2app build configuration.

Usage:
    python setup.py py2app
"""

from setuptools import setup

APP = ["main.py"]
DATA_FILES = [
    ("templates", ["templates/index.html"]),
]
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "resources/AppIcon.icns",   # add your icon here
    "plist": {
        "CFBundleName": "AI Manager",
        "CFBundleDisplayName": "AI Manager",
        "CFBundleIdentifier": "com.benjaminpavelka.aimanager",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0",
        # Keep app alive as menu-bar agent (no Dock icon)
        "LSUIElement": True,
        "NSUserNotificationAlertStyle": "alert",
    },
    "packages": ["flask", "jinja2", "werkzeug", "rumps"],
    "includes": [
        "services_config",
        "backend",
        "menu_bar",
    ],
}

setup(
    app=APP,
    name="AI Manager",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
