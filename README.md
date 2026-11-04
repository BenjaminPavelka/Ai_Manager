<p align="center">
  <img src="resources/logo.png" alt="AI Manager icon" width="128" height="128">
</p>

# AI Manager

[![Build & Release](https://github.com/BenjaminPavelka/Ai_Manager/actions/workflows/release.yml/badge.svg)](https://github.com/BenjaminPavelka/Ai_Manager/actions/workflows/release.yml)
[![Latest Release](https://img.shields.io/github/v/release/BenjaminPavelka/Ai_Manager)](https://github.com/BenjaminPavelka/Ai_Manager/releases/latest)
[![macOS](https://img.shields.io/badge/macOS-12%2B-blue?logo=apple)](https://github.com/BenjaminPavelka/Ai_Manager/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> ⚠️ **Disclaimer:** This app was built by a complete amateur with the generous help of Claude AI.
> It works on my machine. Probably. No warranties, no support, no refunds.
> Use at your own risk — complaints will be cheerfully ignored. 🙃

---

Native macOS menu bar app for managing local AI services, models, and tools.
Lives in the menu bar — always at hand, no unnecessary windows.

<div align="center">
  <img src="screenshots/menubar.png" width="260" alt="Menu bar" />
  &nbsp;&nbsp;&nbsp;
  <img src="screenshots/dashboard.png" width="780" alt="Dashboard" />
</div>

---

## ⬇️ Download

**[→ Download latest release](https://github.com/BenjaminPavelka/Ai_Manager/releases/latest)**

1. Download `AI.Manager.zip` from Releases
2. Unzip and drag `AI Manager.app` to `/Applications`
3. Right-click → **Open** (first launch — bypasses macOS security dialog)

> **Requirement:** [Ollama](https://ollama.ai) installed locally.

---

## Features

| Feature | Description |
|---|---|
| **Menu bar icon** | 🤖 when Ollama is running with a model loaded, 🌙 otherwise |
| **Service status** | Ollama Server and Open WebUI — ● Running / ○ Stopped |
| **Start / Stop** | Control services directly from the menu bar |
| **Models in memory** | Lists all currently loaded Ollama models by name |
| **Mac Apps** | Docker, GitHub Desktop, Goose — status + click to open |
| **Dashboard** | Native app window powered by WebKit — no browser needed |
| **Notifications** | macOS alerts when a service crashes or comes back up |
| **Open at Login** | Toggle auto-start on login directly from the menu |

---

## Architecture

```
main.py              – entry point: Flask thread + rumps on main thread
backend.py           – Flask REST API (/api/* endpoints)
menu_bar.py          – rumps menu bar + crash monitor
dashboard_window.py  – native WebKit window for the dashboard
services_config.py   – service and app configuration (single source of truth)
version.py           – version number
templates/
  index.html         – web dashboard (Bootstrap 5)
resources/           – AppIcon.icns for build, logo.png for README
.github/workflows/
  release.yml      – GitHub Actions: build + GitHub Release on tag push
```

**How it works:**
- Flask runs in a daemon thread on port `7654`
- rumps holds the main thread (macOS requirement for GUI)
- Menu refreshes every 8 s, crash monitor polls every 10 s
- Data (model notes) is stored in `~/Library/Application Support/AI Manager/`

---

## Development

### Requirements

- macOS 12+
- Python 3.11+ (`brew install python`)
- [Ollama](https://ollama.ai)

### Install

```bash
git clone https://github.com/BenjaminPavelka/Ai_Manager.git
cd Ai_Manager
./install.sh
```

`install.sh` creates a virtual environment, installs dependencies, and registers a LaunchAgent (auto-start on login).

### Run manually

```bash
./start.sh
```

### LaunchAgent management

```bash
# Stop
launchctl unload ~/Library/LaunchAgents/com.benjaminpavelka.aimanager.plist

# Start
launchctl load ~/Library/LaunchAgents/com.benjaminpavelka.aimanager.plist

# Log
tail -f ~/Library/Logs/AIManager.log
```

---

## Releasing a new version

```bash
# 1. Update version number
echo 'VERSION = "0.2.0"' > version.py

# 2. Commit + tag
git add version.py
git commit -m "v0.2.0"
git tag v0.2.0
git push && git push --tags
```

GitHub Actions will automatically build the `.app` and create a GitHub Release with the attached `.zip`.

### Semantic versioning

| Version bump | When |
|---|---|
| `0.1.0 → 0.1.1` | Bug fix |
| `0.1.x → 0.2.0` | New feature |
| `0.x.x → 1.0.0` | Stable release |

---

## Adding a new service

In [`services_config.py`](services_config.py):

```python
"my-service": {
    "name":        "My Service",
    "description": "What it does",
    "icon":        "🔧",
    "port":        8888,
    "start_cmd":   ["my-service", "--start"],
    "open_url":    "http://localhost:8888",
},
```

The menu bar, crash monitor, and notifications adapt automatically.

## Adding a new Mac app

In [`services_config.py`](services_config.py):

```python
"my-app": {
    "name":     "My App",
    "icon":     "🛠",
    "app_name": "My App",
    "process":  "My App",
},
```

---

## Old version

The original purely web-based version (Flask + browser) is preserved in [`Old app/`](Old%20app/).
