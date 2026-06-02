# Changelog

All notable changes to AI Manager are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.4.0] – 2026-06-02

### Added
- **Model aliases** – assign a custom display name to any installed model; alias shows prominently, actual model name appears below in smaller text; click the pencil icon to set or edit
- **Restart button** – each service now has a Restart action in the menu bar submenu and in the dashboard (visible when service is running); performs stop → wait → start automatically
- **Activity log** – new "Activity Log" panel at the bottom of the dashboard shows timestamped events (start, stop, restart, model load/unload/pull/delete) with color-coded levels (info / ok / warn / error); auto-refreshes every 5 s; Clear button flushes the buffer
- **Startup healthcheck** – `main.py` now retries the Flask connection up to 10 times before handing off to rumps; if the server never binds, a macOS notification is shown immediately on launch
- **Clickable version label** – "AI Manager vX.Y.Z" in the menu bar now opens GitHub Releases when clicked
- Deleting a model also cleans up its stored alias and note

### Changed
- `backend.py` start/stop logic refactored into `_start_async` / `_stop_sync` helpers used by start, stop, and restart endpoints
- Version bumped to 0.4.0

---

## [0.3.1] – 2026-05-16

### Fixed
- OpenOsint container detection (docker ps filter)
- Switched terminal launcher from Terminal.app to iTerm2

---

## [0.3.0] – 2026-05-16

### Added
- OpenOsint service with Docker container support
- iTerm2 terminal launcher for services with a `cli_cmd`

---

## [0.2.2] – 2026-05-16

### Fixed
- Tools not found when app is launched from Finder (PATH augmentation moved to module level)
