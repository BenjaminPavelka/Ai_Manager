# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A native macOS menu-bar app for managing local AI services (Ollama, Open WebUI, OpenOsint) and Mac apps (Docker, GitHub Desktop, Goose). The app has no Dock icon (`LSUIElement = True`) and lives permanently in the menu bar.

## Development

**Run from source (no build needed):**
```bash
./start.sh
# or
~/ai-manager-venv/bin/python3 main.py
```

**First-time setup (creates venv + LaunchAgent):**
```bash
./install.sh
```

**Build a distributable `.app` (py2app, local):**
```bash
./build.sh
```

**Build with PyInstaller (what CI uses):**
```bash
pyinstaller "AI Manager.spec"
```

There are no tests. Manual testing means running the app and observing the menu bar / dashboard.

**Logs when running via LaunchAgent:**
```bash
tail -f ~/Library/Logs/AIManager.log
```

## Architecture

The entry point is `main.py`: Flask starts in a daemon thread, then `rumps` (the menu-bar framework) takes the main thread — macOS requires all GUI work on the main thread.

- **`backend.py`** — Flask REST API on `localhost:7654`. All service control, model management (list/pull/load/unload/delete), and Mac app status go through `/api/*` endpoints. Long-running operations (pull, load/unload) run in daemon threads and expose polling endpoints (`/api/models/pull/status/<name>`, `/api/models/<name>/op-status`).

- **`menu_bar.py`** — `rumps.App` subclass. Polls `backend.py` every 8 s to refresh service/app status. A separate daemon thread (`_crash_monitor`) polls every 10 s and fires macOS notifications when a service transitions running→stopped or stopped→running. The menu bar icon is `🤖` when Ollama is running with a loaded model, `🌙` otherwise.

- **`dashboard_window.py`** — Opens a native `NSWindow` containing a `WKWebView` pointed at `http://localhost:7654`. Called from the "Open Dashboard" menu item. Keeps a module-level reference to the window to prevent Python GC from destroying it while macOS still holds it.

- **`services_config.py`** — Single source of truth for all services (`SERVICES` dict) and companion Mac apps (`APPS` dict). The `PORT` constant (7654) is also defined here. Both `backend.py` and `menu_bar.py` import from this file. **This is the only file to edit when adding a service or app.**

- **`templates/index.html`** — Bootstrap 5 dashboard served by Flask. Talks to the `/api/*` endpoints via `fetch`.

- **`version.py`** — Single line: `VERSION = "x.y.z"`. Update this before tagging a release.

## Releasing

```bash
echo 'VERSION = "0.x.y"' > version.py
git add version.py && git commit -m "vX.Y.Z"
git tag vX.Y.Z && git push && git push --tags
```

GitHub Actions (`.github/workflows/release.yml`) builds with PyInstaller on `macos-latest` and creates a GitHub Release with `AI.Manager.zip` on any `v*.*.*` tag push.

## Adding a service

Edit `services_config.py`. The menu bar, crash monitor, and `backend.py` all read from `SERVICES` — no other files need changes for a basic service.

For a Docker-container-based service, set `docker_container` to the container name and leave `start_cmd` as `None`. For a port-based service, set `port` and `start_cmd`. Set `cli_cmd` to get a "Open Terminal" submenu that launches iTerm2.

## PyInstaller vs py2app

CI uses PyInstaller with `AI Manager.spec`. Local builds use py2app via `build.sh` / `setup.py`. The two produce equivalent bundles; `AI Manager.spec` is the authoritative build config for releases.

The `sys.frozen` / `sys._MEIPASS` check in `backend.py` resolves the `templates/` path correctly in both dev mode and inside a frozen bundle.
