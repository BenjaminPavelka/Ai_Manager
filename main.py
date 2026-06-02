"""
AI Manager – entry point.

Starts the Flask backend in a background thread, then hands the main thread
to the rumps menu-bar application (required by macOS).
"""

import socket
import threading
import time

from services_config import PORT


def _start_flask():
    from backend import app
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False, threaded=True)


def _flask_healthy(retries: int = 10, interval: float = 0.4) -> bool:
    """Return True once Flask is accepting connections, False if it never starts."""
    for _ in range(retries):
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
                return True
        except OSError:
            time.sleep(interval)
    return False


def main():
    # Flask runs in a daemon thread – it exits when the main thread (rumps) exits
    flask_thread = threading.Thread(target=_start_flask, daemon=True, name="flask")
    flask_thread.start()

    flask_ok = _flask_healthy()

    # rumps MUST run on the main thread (macOS requirement)
    from menu_bar import AIManagerMenuBar
    AIManagerMenuBar(flask_ok=flask_ok).run()


if __name__ == "__main__":
    main()
