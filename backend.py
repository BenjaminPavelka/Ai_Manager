from flask import Flask, render_template, jsonify, request
import subprocess
import socket
import threading
import os
import sys
import time
import json
import datetime
import urllib.request
from collections import deque

from services_config import SERVICES, APPS

# When launched as .app from Finder the PATH is minimal — add common tool locations
os.environ["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")

# Resolve resource path for both dev and PyInstaller frozen bundle
if getattr(sys, "frozen", False):
    _BASE = sys._MEIPASS
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder=os.path.join(_BASE, "templates"))

# Persist data in ~/Library/Application Support/AI Manager (not inside .app)
_APP_SUPPORT = os.path.expanduser("~/Library/Application Support/AI Manager")
os.makedirs(_APP_SUPPORT, exist_ok=True)
NOTES_FILE   = os.path.join(_APP_SUPPORT, "model_notes.json")
ALIASES_FILE = os.path.join(_APP_SUPPORT, "model_aliases.json")


# ── Persistence ────────────────────────────────────────────────────────────────

def load_notes() -> dict:
    try:
        with open(NOTES_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_notes(notes: dict):
    with open(NOTES_FILE, "w") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)


def load_aliases() -> dict:
    try:
        with open(ALIASES_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_aliases(aliases: dict):
    with open(ALIASES_FILE, "w") as f:
        json.dump(aliases, f, ensure_ascii=False, indent=2)


# ── In-memory log ──────────────────────────────────────────────────────────────

_log_buffer: deque = deque(maxlen=200)


def log_event(level: str, msg: str):
    _log_buffer.append({
        "ts":    datetime.datetime.now().strftime("%H:%M:%S"),
        "level": level,   # "info" | "ok" | "warn" | "error"
        "msg":   msg,
    })


_processes: dict[str, subprocess.Popen] = {}
_pull_progress: dict[str, dict] = {}
_model_ops: dict[str, dict] = {}


# ── Helpers ────────────────────────────────────────────────────────────────────

def port_open(port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection(("localhost", port), timeout=timeout):
            return True
    except OSError:
        return False


def docker_installed() -> bool:
    try:
        r = subprocess.run(["which", "docker"], capture_output=True, text=True, timeout=3)
        return r.returncode == 0 and bool(r.stdout.strip())
    except Exception:
        return False


def docker_daemon_running() -> bool:
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=4)
        return r.returncode == 0
    except Exception:
        return False


def docker_container_running(name: str) -> bool:
    try:
        r = subprocess.run(
            ["docker", "ps", "--filter", f"name={name}", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=4,
        )
        return name in r.stdout
    except Exception:
        return False


def _find_docker_container(name: str) -> str | None:
    """Return the actual container name matching `name` (checks stopped containers too)."""
    try:
        r = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={name}", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=4,
        )
        names = [n.strip() for n in r.stdout.splitlines() if n.strip()]
        return names[0] if names else None
    except Exception:
        return None


def service_running(svc: dict) -> bool:
    if svc.get("docker_container"):
        return docker_container_running(svc["docker_container"])
    if svc.get("port"):
        return port_open(svc["port"])
    return False


def detect_open_webui_method() -> str | None:
    if docker_installed():
        return "docker"
    try:
        r = subprocess.run(["which", "open-webui"], capture_output=True, text=True, timeout=3)
        if r.returncode == 0 and r.stdout.strip():
            return "pip"
    except Exception:
        pass
    return None


def kill_port(port: int) -> bool:
    try:
        r = subprocess.run(["lsof", "-ti", f"tcp:{port}"], capture_output=True, text=True)
        pids = [p.strip() for p in r.stdout.splitlines() if p.strip()]
        for pid in pids:
            subprocess.run(["kill", "-9", pid], capture_output=True)
        return bool(pids)
    except Exception:
        return False


def app_running(process_name: str) -> bool:
    try:
        r = subprocess.run(["pgrep", "-ix", process_name], capture_output=True)
        return r.returncode == 0
    except Exception:
        return False


# ── Service start / stop helpers ───────────────────────────────────────────────

def _stop_sync(sid: str, svc: dict):
    """Stop a service synchronously (does not wait for port to close)."""
    if svc.get("docker_container"):
        actual = _find_docker_container(svc["docker_container"]) or svc["docker_container"]
        subprocess.run(["docker", "stop", actual], capture_output=True, timeout=20)
    else:
        kill_port(svc["port"])
    if sid in _processes:
        try:
            _processes[sid].terminate()
        except Exception:
            pass
        _processes.pop(sid, None)


def _start_async(sid: str, svc: dict) -> str | None:
    """Start a service, spinning up background threads for long-running operations.
    Returns an error string on immediate failure, or None if started (or starting)."""
    cmd = svc.get("start_cmd")

    # Docker-container services (openosint, etc.)
    if cmd is None and svc.get("docker_container") and sid != "open-webui":
        container = svc["docker_container"]
        requires = svc.get("requires", [])
        auto_load_model = svc.get("auto_load_model")

        def _start_container(c=container, reqs=requires, model=auto_load_model):
            # Start required services first and wait for them
            for req_sid in reqs:
                req_svc = SERVICES.get(req_sid)
                if not req_svc:
                    continue
                if not service_running(req_svc):
                    log_event("info", f"Starting {req_svc['name']} (required by {svc['name']})")
                    err = _start_async(req_sid, req_svc)
                    if err:
                        log_event("error", f"Failed to start {req_svc['name']}: {err}")
                        return
                    for _ in range(30):
                        time.sleep(2)
                        if service_running(req_svc):
                            break
                    else:
                        log_event("error", f"{req_svc['name']} did not start in time for {svc['name']}")
                        return

            # Trigger model load in background (non-blocking)
            if model:
                log_event("info", f"Loading model {model}")
                _model_ops[model] = {"status": "running", "action": "load"}
                def _load_model(m=model):
                    try:
                        payload = json.dumps({"model": m, "keep_alive": -1, "prompt": ""}).encode()
                        req = urllib.request.Request(
                            "http://localhost:11434/api/generate",
                            data=payload, method="POST",
                            headers={"Content-Type": "application/json"},
                        )
                        with urllib.request.urlopen(req, timeout=300) as resp:
                            resp.read()
                        _model_ops[m] = {"status": "done", "action": "load"}
                        log_event("ok", f"Model loaded: {m}")
                    except Exception as exc:
                        _model_ops[m] = {"status": "error", "action": "load", "error": str(exc)}
                        log_event("error", f"Failed to load model {m}: {exc}")
                threading.Thread(target=_load_model, daemon=True).start()

            if not docker_daemon_running():
                subprocess.Popen(["open", "-a", "Docker"])
                for _ in range(30):
                    time.sleep(2)
                    if docker_daemon_running():
                        break
                else:
                    log_event("error", f"Docker did not start for {svc['name']}")
                    return
            actual = _find_docker_container(c)
            if not actual:
                log_event("error", f"{svc['name']}: no Docker container matching '{c}' — create it first")
                return
            r = subprocess.run(["docker", "start", actual], capture_output=True, text=True)
            if r.returncode != 0:
                log_event("error", f"{svc['name']} docker start failed: {(r.stderr or r.stdout).strip()}")
                return
            log_event("ok", f"{svc['name']} started (Docker: {actual})")
        threading.Thread(target=_start_container, daemon=True).start()
        return None

    if sid == "open-webui" and cmd is None:
        method = detect_open_webui_method()
        if method == "docker":
            def _start_webui_docker():
                if not docker_daemon_running():
                    subprocess.Popen(["open", "-a", "Docker"])
                    for _ in range(30):
                        time.sleep(2)
                        if docker_daemon_running():
                            break
                    else:
                        log_event("error", "Docker did not start for Open WebUI")
                        return
                r = subprocess.run(
                    ["docker", "ps", "-a", "--filter", "name=^open-webui$", "--format", "{{.Names}}"],
                    capture_output=True, text=True,
                )
                if "open-webui" in r.stdout:
                    docker_cmd = ["docker", "start", "open-webui"]
                else:
                    docker_cmd = [
                        "docker", "run", "-d", "--name", "open-webui",
                        "-p", "3000:8080",
                        "--add-host=host.docker.internal:host-gateway",
                        "-v", "open-webui:/app/backend/data",
                        "--restart", "always",
                        "ghcr.io/open-webui/open-webui:main",
                    ]
                subprocess.run(docker_cmd, capture_output=True)
                log_event("ok", "Open WebUI started (Docker)")
            threading.Thread(target=_start_webui_docker, daemon=True).start()
            return None
        elif method == "pip":
            cmd = ["open-webui", "serve"]
        else:
            return "Open WebUI is not installed (neither Docker nor pip)"

    if cmd:
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True
            )
            _processes[sid] = proc
            log_event("ok", f"{svc['name']} started")
            return None
        except FileNotFoundError as exc:
            return f"Command not found: {exc}"
        except Exception as exc:
            return str(exc)

    return "No start command configured"


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    result = {}
    for sid, svc in SERVICES.items():
        running = service_running(svc)
        result[sid] = {
            "name":        svc["name"],
            "description": svc["description"],
            "icon":        svc["icon"],
            "running":     running,
            "open_url":    svc.get("open_url"),
            "cli_cmd":     svc.get("cli_cmd"),
        }
    return jsonify(result)


@app.route("/api/services/<sid>/start", methods=["POST"])
def start_service(sid: str):
    if sid not in SERVICES:
        return jsonify({"error": "Unknown service"}), 404
    svc = SERVICES[sid]
    if service_running(svc):
        return jsonify({"ok": True, "msg": "Already running"})
    log_event("info", f"Starting {svc['name']}")
    err = _start_async(sid, svc)
    if err:
        log_event("error", f"Failed to start {svc['name']}: {err}")
        return jsonify({"error": err}), 500
    return jsonify({"ok": True})


@app.route("/api/services/<sid>/stop", methods=["POST"])
def stop_service(sid: str):
    if sid not in SERVICES:
        return jsonify({"error": "Unknown service"}), 404
    svc = SERVICES[sid]
    log_event("info", f"Stopping {svc['name']}")
    try:
        _stop_sync(sid, svc)
        log_event("ok", f"{svc['name']} stopped")
        return jsonify({"ok": True})
    except Exception as exc:
        log_event("error", f"Stop failed for {svc['name']}: {exc}")
        return jsonify({"error": str(exc)}), 500


@app.route("/api/services/<sid>/restart", methods=["POST"])
def restart_service(sid: str):
    if sid not in SERVICES:
        return jsonify({"error": "Unknown service"}), 404
    svc = SERVICES[sid]
    log_event("info", f"Restarting {svc['name']}")

    def _do_restart():
        _stop_sync(sid, svc)
        # Wait until the service actually stops (max 10 s)
        for _ in range(20):
            time.sleep(0.5)
            if not service_running(svc):
                break
        time.sleep(0.3)
        err = _start_async(sid, svc)
        if err:
            log_event("error", f"Restart failed for {svc['name']}: {err}")

    threading.Thread(target=_do_restart, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/services/stop-all", methods=["POST"])
def stop_all_services():
    def _worker():
        # Unload all loaded models first
        try:
            with urllib.request.urlopen("http://localhost:11434/api/ps", timeout=3) as resp:
                ps = json.loads(resp.read())
            for m in ps.get("models", []):
                name = m["name"]
                try:
                    payload = json.dumps({"model": name, "keep_alive": 0, "prompt": ""}).encode()
                    req = urllib.request.Request(
                        "http://localhost:11434/api/generate",
                        data=payload, method="POST",
                        headers={"Content-Type": "application/json"},
                    )
                    with urllib.request.urlopen(req, timeout=30) as r:
                        r.read()
                    log_event("ok", f"Model unloaded: {name}")
                except Exception:
                    pass
        except Exception:
            pass

        # Stop services — ollama last so other services can shut down cleanly
        order = [sid for sid in SERVICES if sid != "ollama"] + ["ollama"]
        for sid in order:
            svc = SERVICES[sid]
            if service_running(svc):
                try:
                    _stop_sync(sid, svc)
                    log_event("ok", f"{svc['name']} stopped")
                except Exception as exc:
                    log_event("error", f"Stop failed for {svc['name']}: {exc}")

    log_event("info", "Stopping all services")
    threading.Thread(target=_worker, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/services/<sid>/terminal", methods=["POST"])
def open_terminal(sid: str):
    if sid not in SERVICES:
        return jsonify({"error": "Unknown service"}), 404
    cli_cmd = SERVICES[sid].get("cli_cmd")
    if not cli_cmd:
        return jsonify({"error": "No CLI command configured for this service"}), 400
    try:
        script = (
            'tell application "iTerm2"\n'
            '    activate\n'
            '    tell (create window with default profile)\n'
            '        tell current session\n'
            f'            write text "{cli_cmd}"\n'
            '        end tell\n'
            '    end tell\n'
            'end tell'
        )
        subprocess.Popen(["osascript", "-e", script])
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ── Logs ───────────────────────────────────────────────────────────────────────

@app.route("/api/logs")
def api_logs():
    n = min(int(request.args.get("n", 100)), 200)
    return jsonify(list(_log_buffer)[-n:])


@app.route("/api/logs", methods=["DELETE"])
def clear_logs():
    _log_buffer.clear()
    return jsonify({"ok": True})


# ── Models ─────────────────────────────────────────────────────────────────────

@app.route("/api/models")
def api_models():
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return jsonify({"error": r.stderr.strip(), "models": []})
        lines = r.stdout.strip().splitlines()
        models = []
        for line in lines[1:]:
            parts = line.split()
            if not parts:
                continue
            name = parts[0]
            id_ = parts[1] if len(parts) > 1 else ""
            if len(parts) >= 4 and parts[3] in ("GB", "MB", "KB", "B"):
                size     = parts[2] + " " + parts[3]
                modified = " ".join(parts[4:])
            else:
                size     = parts[2] if len(parts) > 2 else ""
                modified = " ".join(parts[3:]) if len(parts) > 3 else ""
            models.append({"name": name, "id": id_, "size": size, "modified": modified})
        return jsonify({"models": models})
    except FileNotFoundError:
        return jsonify({"error": "Ollama is not installed", "models": []})
    except Exception as exc:
        return jsonify({"error": str(exc), "models": []})


@app.route("/api/models/notes")
def api_model_notes():
    return jsonify(load_notes())


@app.route("/api/models/<path:name>/note", methods=["POST"])
def set_model_note(name: str):
    body = request.get_json(silent=True) or {}
    note = body.get("note", "").strip()
    notes = load_notes()
    if note:
        notes[name] = note
    else:
        notes.pop(name, None)
    save_notes(notes)
    return jsonify({"ok": True})


@app.route("/api/models/aliases")
def api_model_aliases():
    return jsonify(load_aliases())


@app.route("/api/models/<path:name>/alias", methods=["POST"])
def set_model_alias(name: str):
    body = request.get_json(silent=True) or {}
    alias = body.get("alias", "").strip()
    aliases = load_aliases()
    if alias:
        aliases[name] = alias
    else:
        aliases.pop(name, None)
    save_aliases(aliases)
    return jsonify({"ok": True})


@app.route("/api/models/running")
def api_models_running():
    try:
        import urllib.request, json as _json
        with urllib.request.urlopen("http://localhost:11434/api/ps", timeout=3) as resp:
            data = _json.loads(resp.read())
        names = [m["name"] for m in data.get("models", [])]
        return jsonify({"running": names})
    except Exception:
        return jsonify({"running": []})


@app.route("/api/models/<path:name>/load", methods=["POST"])
def load_model(name: str):
    if not port_open(11434):
        return jsonify({"error": "ollama_not_running"}), 503
    log_event("info", f"Loading model: {name}")
    _model_ops[name] = {"status": "running", "action": "load"}

    def worker():
        try:
            import urllib.request
            payload = json.dumps({"model": name, "keep_alive": -1, "prompt": ""}).encode()
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=payload, method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                resp.read()
            _model_ops[name] = {"status": "done", "action": "load"}
            log_event("ok", f"Model loaded: {name}")
        except Exception as exc:
            _model_ops[name] = {"status": "error", "action": "load", "error": str(exc)}
            log_event("error", f"Failed to load model {name}: {exc}")

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/models/<path:name>/unload", methods=["POST"])
def unload_model(name: str):
    log_event("info", f"Unloading model: {name}")
    _model_ops[name] = {"status": "running", "action": "unload"}

    def worker():
        try:
            import urllib.request
            payload = json.dumps({"model": name, "keep_alive": 0, "prompt": ""}).encode()
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=payload, method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp.read()
            # Wait until Ollama confirms the model is gone from /api/ps
            for _ in range(20):
                time.sleep(0.5)
                try:
                    with urllib.request.urlopen("http://localhost:11434/api/ps", timeout=3) as r:
                        ps = json.loads(r.read())
                    if name not in [m["name"] for m in ps.get("models", [])]:
                        break
                except Exception:
                    break
            _model_ops[name] = {"status": "done", "action": "unload"}
            log_event("ok", f"Model unloaded: {name}")
        except Exception as exc:
            _model_ops[name] = {"status": "error", "action": "unload", "error": str(exc)}
            log_event("error", f"Failed to unload model {name}: {exc}")

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/models/<path:name>/op-status")
def model_op_status(name: str):
    return jsonify(_model_ops.get(name, {"status": "idle"}))


@app.route("/api/models/pull", methods=["POST"])
def pull_model():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Model name is required"}), 400

    if name in _pull_progress and _pull_progress[name].get("status") == "pulling":
        return jsonify({"ok": True, "msg": "Already downloading"})

    log_event("info", f"Pulling model: {name}")
    _pull_progress[name] = {"status": "pulling", "lines": [], "pct": 0}

    def worker():
        try:
            proc = subprocess.Popen(
                ["ollama", "pull", name],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            for raw in proc.stdout:
                line = raw.strip()
                if not line:
                    continue
                entry = _pull_progress[name]
                entry["lines"].append(line)
                entry["lines"] = entry["lines"][-30:]
                if "%" in line:
                    for part in line.split():
                        part = part.strip("%")
                        if part.isdigit():
                            entry["pct"] = int(part)
                            break
            proc.wait()
            _pull_progress[name]["status"] = "done" if proc.returncode == 0 else "error"
            _pull_progress[name]["pct"] = 100 if proc.returncode == 0 else _pull_progress[name]["pct"]
            if proc.returncode == 0:
                log_event("ok", f"Model downloaded: {name}")
            else:
                log_event("error", f"Model download failed: {name}")
        except Exception as exc:
            _pull_progress[name] = {"status": "error", "lines": [str(exc)], "pct": 0}
            log_event("error", f"Pull error for {name}: {exc}")

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/models/pull/status/<path:name>")
def pull_status(name: str):
    return jsonify(_pull_progress.get(name, {"status": "not_started", "lines": [], "pct": 0}))


@app.route("/api/models/<path:name>", methods=["DELETE"])
def delete_model(name: str):
    log_event("info", f"Deleting model: {name}")
    try:
        r = subprocess.run(["ollama", "rm", name], capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            # Clean up alias and note for the deleted model
            aliases = load_aliases()
            if name in aliases:
                aliases.pop(name)
                save_aliases(aliases)
            notes = load_notes()
            if name in notes:
                notes.pop(name)
                save_notes(notes)
            log_event("ok", f"Model deleted: {name}")
            return jsonify({"ok": True})
        log_event("error", f"Delete failed for {name}: {r.stderr.strip()}")
        return jsonify({"error": r.stderr.strip()}), 500
    except Exception as exc:
        log_event("error", f"Delete error for {name}: {exc}")
        return jsonify({"error": str(exc)}), 500


# ── Mac Apps ───────────────────────────────────────────────────────────────────

@app.route("/api/apps/status")
def api_apps_status():
    return jsonify({
        aid: {
            "name":    a["name"],
            "icon":    a["icon"],
            "running": app_running(a["process"]),
        }
        for aid, a in APPS.items()
    })


@app.route("/api/apps/<aid>/open", methods=["POST"])
def open_app(aid: str):
    if aid not in APPS:
        return jsonify({"error": "Unknown app"}), 404
    try:
        subprocess.Popen(["open", "-a", APPS[aid]["app_name"]])
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
