from flask import Flask, render_template, jsonify, request
import subprocess
import socket
import threading
import os
import time
import json

app = Flask(__name__)

NOTES_FILE = os.path.join(os.path.dirname(__file__), "model_notes.json")

def load_notes() -> dict:
    try:
        with open(NOTES_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def save_notes(notes: dict):
    with open(NOTES_FILE, "w") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)

# ── Service definitions ────────────────────────────────────────────────────────

SERVICES = {
    "ollama": {
        "name": "Ollama Server",
        "description": "Lokální LLM inference server",
        "icon": "🦙",
        "port": 11434,
        "start_cmd": ["ollama", "serve"],
        "open_url": None,
    },
    "open-webui": {
        "name": "Open WebUI",
        "description": "Webové UI pro chat s lokálními modely",
        "icon": "🌐",
        "port": 3000,
        "start_cmd": None,   # detected at runtime
        "open_url": "http://localhost:3000",
    },
}

APPS = {
    "docker": {
        "name": "Docker",
        "icon": "🐳",
        "app_name": "Docker",          # name passed to `open -a`
        "process":  "Docker Desktop",  # name used by pgrep
    },
    "github-desktop": {
        "name": "GitHub Desktop",
        "icon": "🐙",
        "app_name": "GitHub Desktop",
        "process":  "GitHub Desktop",
    },
    "goose": {
        "name": "Goose",
        "icon": "🪿",
        "app_name": "Goose",
        "process":  "Goose",
    },
}

_processes: dict[str, subprocess.Popen] = {}
_pull_progress: dict[str, dict] = {}


# ── Helpers ────────────────────────────────────────────────────────────────────

def port_open(port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection(("localhost", port), timeout=timeout):
            return True
    except OSError:
        return False


def detect_open_webui_method() -> str | None:
    """Return 'docker', 'pip', or None."""
    try:
        r = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=open-webui", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=4,
        )
        if r.returncode == 0 and "open-webui" in r.stdout:
            return "docker"
    except Exception:
        pass

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


# ── API ────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    result = {}
    for sid, svc in SERVICES.items():
        running = port_open(svc["port"])
        result[sid] = {
            "name": svc["name"],
            "description": svc["description"],
            "icon": svc["icon"],
            "running": running,
            "open_url": svc.get("open_url"),
        }
    return jsonify(result)


@app.route("/api/services/<sid>/start", methods=["POST"])
def start_service(sid: str):
    if sid not in SERVICES:
        return jsonify({"error": "Neznámá služba"}), 404

    svc = SERVICES[sid]

    if port_open(svc["port"]):
        return jsonify({"ok": True, "msg": "Již běží"})

    # Determine start command
    cmd = svc["start_cmd"]

    if sid == "open-webui" and cmd is None:
        method = detect_open_webui_method()
        if method == "docker":
            # Check if container already exists (running or stopped)
            r = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=^open-webui$", "--format", "{{.Names}}"],
                capture_output=True, text=True,
            )
            container_exists = "open-webui" in r.stdout
            if container_exists:
                cmd = ["docker", "start", "open-webui"]
            else:
                cmd = [
                    "docker", "run", "-d", "--name", "open-webui",
                    "-p", "3000:8080",
                    "--add-host=host.docker.internal:host-gateway",
                    "-v", "open-webui:/app/backend/data",
                    "--restart", "always",
                    "ghcr.io/open-webui/open-webui:main",
                ]
        elif method == "pip":
            cmd = ["open-webui", "serve"]
        else:
            return jsonify({"error": "Open WebUI není nainstalováno (Docker ani pip)"}), 500

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        _processes[sid] = proc
        return jsonify({"ok": True})
    except FileNotFoundError as exc:
        return jsonify({"error": f"Příkaz nenalezen: {exc}"}), 500
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/services/<sid>/stop", methods=["POST"])
def stop_service(sid: str):
    if sid not in SERVICES:
        return jsonify({"error": "Neznámá služba"}), 404

    svc = SERVICES[sid]

    # Docker stop
    if sid == "open-webui" and detect_open_webui_method() == "docker":
        try:
            subprocess.run(["docker", "stop", "open-webui"], capture_output=True, timeout=15)
            _processes.pop(sid, None)
            return jsonify({"ok": True})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # Kill by port
    killed = kill_port(svc["port"])

    # Also kill tracked process
    if sid in _processes:
        try:
            _processes[sid].terminate()
        except Exception:
            pass
        _processes.pop(sid, None)

    if killed:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "msg": "Žádný proces na daném portu nenalezen"})


# ── Models ─────────────────────────────────────────────────────────────────────

@app.route("/api/models")
def api_models():
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return jsonify({"error": r.stderr.strip(), "models": []})

        lines = r.stdout.strip().splitlines()
        models = []
        for line in lines[1:]:   # skip header
            parts = line.split()
            if not parts:
                continue
            # ollama list columns: NAME  ID  SIZE  SIZE_UNIT  MODIFIED...
            name = parts[0]
            id_  = parts[1] if len(parts) > 1 else ""
            if len(parts) >= 4 and parts[3] in ("GB", "MB", "KB", "B"):
                size     = parts[2] + " " + parts[3]
                modified = " ".join(parts[4:])
            else:
                size     = parts[2] if len(parts) > 2 else ""
                modified = " ".join(parts[3:]) if len(parts) > 3 else ""
            models.append({"name": name, "id": id_, "size": size, "modified": modified})
        return jsonify({"models": models})
    except FileNotFoundError:
        return jsonify({"error": "Ollama není nainstalována", "models": []})
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


@app.route("/api/models/running")
def api_models_running():
    """Returns models currently loaded in Ollama memory (via /api/ps)."""
    try:
        import urllib.request, json as _json
        with urllib.request.urlopen("http://localhost:11434/api/ps", timeout=3) as resp:
            data = _json.loads(resp.read())
        names = [m["name"] for m in data.get("models", [])]
        return jsonify({"running": names})
    except Exception:
        return jsonify({"running": []})


_model_ops: dict[str, dict] = {}   # tracks in-progress load/unload ops


@app.route("/api/models/<path:name>/load", methods=["POST"])
def load_model(name: str):
    if not port_open(11434):
        return jsonify({"error": "ollama_not_running"}), 503

    _model_ops[name] = {"status": "running", "action": "load"}

    def worker():
        try:
            import urllib.request
            payload = json.dumps({"model": name, "keep_alive": -1}).encode()
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=payload, method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120):
                pass
            _model_ops[name] = {"status": "done", "action": "load"}
        except Exception as exc:
            _model_ops[name] = {"status": "error", "action": "load", "error": str(exc)}

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/models/<path:name>/unload", methods=["POST"])
def unload_model(name: str):
    _model_ops[name] = {"status": "running", "action": "unload"}

    def worker():
        try:
            import urllib.request
            payload = json.dumps({"model": name, "keep_alive": 0}).encode()
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=payload, method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30):
                pass
            _model_ops[name] = {"status": "done", "action": "unload"}
        except Exception as exc:
            _model_ops[name] = {"status": "error", "action": "unload", "error": str(exc)}

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
        return jsonify({"error": "Chybí název modelu"}), 400

    if name in _pull_progress and _pull_progress[name].get("status") == "pulling":
        return jsonify({"ok": True, "msg": "Již se stahuje"})

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
                entry["lines"] = entry["lines"][-30:]   # keep last 30
                # Try to parse percentage
                if "%" in line:
                    for part in line.split():
                        part = part.strip("%")
                        if part.isdigit():
                            entry["pct"] = int(part)
                            break
            proc.wait()
            _pull_progress[name]["status"] = "done" if proc.returncode == 0 else "error"
            _pull_progress[name]["pct"] = 100 if proc.returncode == 0 else _pull_progress[name]["pct"]
        except Exception as exc:
            _pull_progress[name] = {"status": "error", "lines": [str(exc)], "pct": 0}

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/models/pull/status/<path:name>")
def pull_status(name: str):
    return jsonify(_pull_progress.get(name, {"status": "not_started", "lines": [], "pct": 0}))


@app.route("/api/models/<path:name>", methods=["DELETE"])
def delete_model(name: str):
    try:
        r = subprocess.run(["ollama", "rm", name], capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            return jsonify({"ok": True})
        return jsonify({"error": r.stderr.strip()}), 500
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ── Mac Apps ──────────────────────────────────────────────────────────────────

def app_running(process_name: str) -> bool:
    try:
        r = subprocess.run(["pgrep", "-ix", process_name], capture_output=True)
        return r.returncode == 0
    except Exception:
        return False


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
        return jsonify({"error": "Neznámá aplikace"}), 404
    try:
        subprocess.Popen(["open", "-a", APPS[aid]["app_name"]])
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ── Launch ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import webbrowser

    def _open_browser():
        time.sleep(1.2)
        webbrowser.open("http://localhost:7654")

    threading.Thread(target=_open_browser, daemon=True).start()
    print("🚀 AI Manager běží na http://localhost:7654")
    app.run(host="127.0.0.1", port=7654, debug=False)
