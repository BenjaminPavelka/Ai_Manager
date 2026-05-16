"""
AI Manager – entry point.

Starts the Flask backend in a background thread, then hands the main thread
to the rumps menu-bar application (required by macOS).
"""

import threading
import time

from services_config import PORT


def _start_flask():
    from backend import app
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False, threaded=True)


def main():
    # Flask runs in a daemon thread – it exits when the main thread (rumps) exits
    flask_thread = threading.Thread(target=_start_flask, daemon=True, name="flask")
    flask_thread.start()

    # Give Flask a moment to bind the port before rumps opens
    time.sleep(0.8)

    # rumps MUST run on the main thread (macOS requirement)
    from menu_bar import AIManagerMenuBar
    AIManagerMenuBar().run()


if __name__ == "__main__":
    main()
