import socket
import subprocess
import threading
import time
import urllib.request
import json
import webbrowser

import rumps

from services_config import SERVICES, APPS, PORT

# How often (seconds) the menu refreshes service statuses
REFRESH_INTERVAL = 8

# How often the crash-monitor polls (separate from menu refresh)
MONITOR_INTERVAL = 10


class AIManagerMenuBar(rumps.App):
    def __init__(self):
        super().__init__("AI Manager", title="🤖", quit_button=None)

        self._prev_states: dict[str, bool | None] = {sid: None for sid in SERVICES}
        self._service_menu_items: dict[str, rumps.MenuItem] = {}
        self._app_menu_items: dict[str, rumps.MenuItem] = {}

        self._build_menu()
        self._refresh_status(None)

        # Timer: refresh menu items every REFRESH_INTERVAL seconds
        self._refresh_timer = rumps.Timer(self._refresh_status, REFRESH_INTERVAL)
        self._refresh_timer.start()

        # Background crash monitor (finer-grained, fires notifications)
        threading.Thread(target=self._crash_monitor, daemon=True).start()

    # ── Menu construction ──────────────────────────────────────────────────────

    def _build_menu(self):
        open_dashboard = rumps.MenuItem(
            "📊  Otevřít Dashboard",
            callback=lambda _: webbrowser.open(f"http://localhost:{PORT}"),
        )

        service_items = []
        for sid, svc in SERVICES.items():
            parent = rumps.MenuItem(f"{svc['icon']}  {svc['name']}")

            start_item = rumps.MenuItem("  ▶  Spustit", callback=self._make_action(sid, "start"))
            stop_item  = rumps.MenuItem("  ■  Zastavit", callback=self._make_action(sid, "stop"))

            if svc.get("open_url"):
                open_item = rumps.MenuItem(
                    "  ↗  Otevřít v prohlížeči",
                    callback=lambda _, u=svc["open_url"]: webbrowser.open(u),
                )
                parent.add(open_item)
                parent.add(None)

            parent.add(start_item)
            parent.add(stop_item)

            self._service_menu_items[sid] = parent
            service_items.append(parent)

        # Running models – dynamic submenu rebuilt on every refresh
        self._models_parent = rumps.MenuItem("💾  Modely v paměti (0)")

        # Mac Apps – fixed items, dynamic titles, click = open
        app_items = []
        for aid, acfg in APPS.items():
            item = rumps.MenuItem(
                f"{acfg['icon']}  {acfg['name']}",
                callback=self._make_open_app(aid),
            )
            self._app_menu_items[aid] = item
            app_items.append(item)

        quit_item = rumps.MenuItem("Ukončit", callback=lambda _: rumps.quit_application())

        self.menu = [
            open_dashboard,
            None,
            *service_items,
            None,
            self._models_parent,
            None,
            *app_items,
            None,
            quit_item,
        ]

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

    def _call_api(self, path: str, method: str = "POST"):
        try:
            req = urllib.request.Request(
                f"http://localhost:{PORT}{path}",
                data=b"",
                method=method,
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
    def _app_running(process_name: str) -> bool:
        try:
            return subprocess.run(["pgrep", "-ix", process_name], capture_output=True).returncode == 0
        except Exception:
            return False

    # ── Status refresh (timer callback – runs on main thread) ─────────────────

    def _refresh_status(self, _sender):
        for sid, svc in SERVICES.items():
            running = self._port_open(svc["port"])
            dot = "●" if running else "○"
            label = "Běží" if running else "Zastaveno"
            self._service_menu_items[sid].title = f"{svc['icon']}  {svc['name']}  {dot} {label}"

        # Running models – rebuild submenu
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
            self._models_parent.add(rumps.MenuItem("  Žádný model v paměti"))
        self._models_parent.title = f"💾  Modely v paměti ({len(models)})"

        # Mac Apps
        for aid, acfg in APPS.items():
            running = self._app_running(acfg["process"])
            dot = "●" if running else "○"
            self._app_menu_items[aid].title = f"{acfg['icon']}  {acfg['name']}  {dot}"

        ollama_running = self._port_open(SERVICES["ollama"]["port"])
        self.title = "🤖" if (ollama_running and models) else "🌙"

    # ── Crash monitor (background thread – only sends notifications) ───────────

    def _crash_monitor(self):
        # Give Flask a moment to start before first check
        time.sleep(5)

        while True:
            for sid, svc in SERVICES.items():
                running = self._port_open(svc["port"])
                prev = self._prev_states.get(sid)

                if prev is True and not running:
                    rumps.notification(
                        title=f"⚠️  {svc['name']} spadlo",
                        subtitle="AI Manager",
                        message="Služba přestala odpovídat.",
                        sound=True,
                    )
                elif prev is False and running:
                    rumps.notification(
                        title=f"✅  {svc['name']} spuštěno",
                        subtitle="AI Manager",
                        message="Služba je nyní dostupná.",
                        sound=False,
                    )

                self._prev_states[sid] = running

            time.sleep(MONITOR_INTERVAL)
