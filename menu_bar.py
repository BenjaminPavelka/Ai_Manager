import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import json
import webbrowser
import rumps

from services_config import SERVICES, APPS, PORT
from version import VERSION
import dashboard_window

os.environ["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")

REFRESH_INTERVAL = 8
MONITOR_INTERVAL = 10

PLIST_PATH = os.path.expanduser("~/Library/LaunchAgents/com.benjaminpavelka.aimanager.plist")


class AIManagerMenuBar(rumps.App):
    def __init__(self, flask_ok: bool = True):
        super().__init__("AI Manager", title="🤖", quit_button=None)

        if not flask_ok:
            rumps.notification(
                title="AI Manager – startup error",
                subtitle="",
                message="Internal server failed to start. Please restart the app.",
                sound=True,
            )

        self._prev_states: dict[str, bool | None] = {sid: None for sid in SERVICES}
        self._service_menu_items: dict[str, rumps.MenuItem] = {}
        self._app_menu_items: dict[str, rumps.MenuItem] = {}

        self._build_menu()
        self._refresh_status(None)

        self._refresh_timer = rumps.Timer(self._refresh_status, REFRESH_INTERVAL)
        self._refresh_timer.start()

        threading.Thread(target=self._crash_monitor, daemon=True).start()

    # ── Menu construction ──────────────────────────────────────────────────────

    def _build_menu(self):
        open_dashboard = rumps.MenuItem(
            "📊  Open Dashboard",
            callback=lambda _: dashboard_window.open_dashboard(),
        )

        service_items = []
        for sid, svc in SERVICES.items():
            parent = rumps.MenuItem(f"{svc['icon']}  {svc['name']}")
            if svc.get("open_url"):
                parent.add(rumps.MenuItem(
                    "  ↗  Open in Browser",
                    callback=lambda _, u=svc["open_url"]: webbrowser.open(u),
                ))
                parent.add(None)
            if svc.get("cli_cmd"):
                parent.add(rumps.MenuItem(
                    "  >_  Open Terminal",
                    callback=lambda _, c=svc["cli_cmd"]: self._open_terminal(c),
                ))
                parent.add(None)
            parent.add(rumps.MenuItem("  ▶  Start",   callback=self._make_action(sid, "start")))
            parent.add(rumps.MenuItem("  ■  Stop",    callback=self._make_action(sid, "stop")))
            parent.add(rumps.MenuItem("  ↺  Restart", callback=self._make_action(sid, "restart")))
            self._service_menu_items[sid] = parent
            service_items.append(parent)

        self._models_parent = rumps.MenuItem("💾  Models in Memory (0)")

        app_items = []
        for aid, acfg in APPS.items():
            item = rumps.MenuItem(
                f"{acfg['icon']}  {acfg['name']}",
                callback=self._make_open_app(aid),
            )
            self._app_menu_items[aid] = item
            app_items.append(item)

        self._login_item = rumps.MenuItem(
            "Open at Login",
            callback=self._toggle_login_item,
        )
        self._login_item.state = self._login_item_enabled()

        about_item = rumps.MenuItem(
            f"AI Manager  v{VERSION}",
            callback=lambda _: webbrowser.open(
                "https://github.com/BenjaminPavelka/Ai_Manager_Claud_APP/releases"
            ),
        )
        quit_item  = rumps.MenuItem("Quit", callback=lambda _: rumps.quit_application())

        self.menu = [
            open_dashboard,
            None,
            *service_items,
            None,
            self._models_parent,
            None,
            *app_items,
            None,
            self._login_item,
            about_item,
            quit_item,
        ]

    # ── Open at Login ──────────────────────────────────────────────────────────

    def _login_item_enabled(self) -> bool:
        if getattr(sys, "frozen", False):
            r = subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to return name of every login item'],
                capture_output=True, text=True,
            )
            return "AI Manager" in r.stdout
        return os.path.exists(PLIST_PATH)

    def _toggle_login_item(self, sender):
        enabled = self._login_item_enabled()
        if getattr(sys, "frozen", False):
            if enabled:
                subprocess.run(
                    ["osascript", "-e",
                     'tell application "System Events" to delete login item "AI Manager"'],
                    capture_output=True,
                )
            else:
                app_path = os.path.abspath(
                    os.path.join(os.path.dirname(sys.executable), "..", "..")
                )
                subprocess.run(
                    ["osascript", "-e",
                     f'tell application "System Events" to make login item at end '
                     f'with properties {{path:"{app_path}", hidden:false}}'],
                    capture_output=True,
                )
        else:
            if enabled:
                subprocess.run(["launchctl", "unload", PLIST_PATH], capture_output=True)
            else:
                subprocess.run(["launchctl", "load", PLIST_PATH], capture_output=True)

        sender.state = not enabled

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _make_action(self, sid: str, action: str):
        def callback(_):
            threading.Thread(
                target=self._call_api,
                args=(f"/api/services/{sid}/{action}",),
                daemon=True,
            ).start()
        return callback

    def _make_open_app(self, aid: str):
        def callback(_):
            subprocess.Popen(["open", "-a", APPS[aid]["app_name"]])
        return callback

    def _call_api(self, path: str):
        try:
            req = urllib.request.Request(
                f"http://localhost:{PORT}{path}", data=b"", method="POST"
            )
            with urllib.request.urlopen(req, timeout=5):
                pass
        except Exception:
            pass

    @staticmethod
    def _port_open(port: int) -> bool:
        try:
            with socket.create_connection(("localhost", port), timeout=1.5):
                return True
        except OSError:
            return False

    @staticmethod
    def _docker_container_running(name: str) -> bool:
        try:
            r = subprocess.run(
                ["docker", "ps", "--filter", f"name={name}", "--format", "{{.Names}}"],
                capture_output=True, text=True, timeout=4,
            )
            return name in r.stdout
        except Exception:
            return False

    def _service_running(self, svc: dict) -> bool:
        if svc.get("docker_container"):
            return self._docker_container_running(svc["docker_container"])
        if svc.get("port"):
            return self._port_open(svc["port"])
        return False

    @staticmethod
    def _open_terminal(cmd: str):
        script = (
            'tell application "iTerm2"\n'
            '    activate\n'
            '    tell (create window with default profile)\n'
            '        tell current session\n'
            f'            write text "{cmd}"\n'
            '        end tell\n'
            '    end tell\n'
            'end tell'
        )
        subprocess.Popen(["osascript", "-e", script])

    @staticmethod
    def _app_running(process_name: str) -> bool:
        try:
            return subprocess.run(
                ["pgrep", "-ix", process_name], capture_output=True
            ).returncode == 0
        except Exception:
            return False

    # ── Status refresh ─────────────────────────────────────────────────────────

    def _refresh_status(self, _sender):
        for sid, svc in SERVICES.items():
            running = self._service_running(svc)
            dot   = "●" if running else "○"
            label = "Running" if running else "Stopped"
            self._service_menu_items[sid].title = f"{svc['icon']}  {svc['name']}  {dot} {label}"

        try:
            with urllib.request.urlopen(
                f"http://localhost:{PORT}/api/models/running", timeout=2
            ) as resp:
                data = json.loads(resp.read())
            models = data.get("running", [])
        except Exception:
            models = []

        for key in list(self._models_parent.keys()):
            del self._models_parent[key]
        if models:
            for m in models:
                self._models_parent.add(rumps.MenuItem(f"  ⚡  {m}"))
        else:
            self._models_parent.add(rumps.MenuItem("  No models loaded"))
        self._models_parent.title = f"💾  Models in Memory ({len(models)})"

        for aid, acfg in APPS.items():
            running = self._app_running(acfg["process"])
            dot = "●" if running else "○"
            self._app_menu_items[aid].title = f"{acfg['icon']}  {acfg['name']}  {dot}"

        ollama_running = self._service_running(SERVICES["ollama"])
        self.title = "🤖" if (ollama_running and models) else "🌙"

    # ── Crash monitor ──────────────────────────────────────────────────────────

    def _crash_monitor(self):
        time.sleep(5)
        while True:
            for sid, svc in SERVICES.items():
                running = self._service_running(svc)
                prev = self._prev_states.get(sid)
                if prev is True and not running:
                    rumps.notification(
                        title=f"⚠️  {svc['name']} stopped",
                        subtitle="AI Manager",
                        message="Service is no longer responding.",
                        sound=True,
                    )
                elif prev is False and running:
                    rumps.notification(
                        title=f"✅  {svc['name']} started",
                        subtitle="AI Manager",
                        message="Service is now available.",
                        sound=False,
                    )
                self._prev_states[sid] = running
            time.sleep(MONITOR_INTERVAL)
