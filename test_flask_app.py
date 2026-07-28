"""Launch the SURFs_UP Flask interface locally for manual testing."""

from __future__ import annotations

import threading
import webbrowser

from surfs_up.web import create_app
from surfs_up.jobs import run_worker


HOST = "127.0.0.1"
PORT = 5000


def open_browser() -> None:
    """Open the test site shortly after the development server starts."""
    webbrowser.open(f"http://{HOST}:{PORT}")


def main() -> None:
    """Start the Flask development server and display it in a browser."""
    app = create_app({"TESTING": True, "RUN_JOBS_SYNCHRONOUS": False})
    threading.Thread(target=run_worker, daemon=True, name="surfs-up-worker").start()
    threading.Timer(1.0, open_browser).start()
    app.run(host=HOST, port=PORT, debug=True, use_reloader=False)


if __name__ == "__main__":
    main()
