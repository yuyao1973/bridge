"""Desktop entry point for the PyInstaller-packaged Streamlit app."""

from __future__ import annotations

import multiprocessing
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


DEFAULT_PORT = 8501


def base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent


def app_file() -> Path:
    return base_path() / "app.py"


def open_browser(port: int) -> None:
    time.sleep(1.8)
    webbrowser.open(f"http://localhost:{port}")


def main() -> int:
    os.chdir(base_path())
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
    os.environ.setdefault("STREAMLIT_GLOBAL_DEVELOPMENT_MODE", "false")
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")

    app_path = app_file()
    if not app_path.is_file():
        print(f"找不到应用文件：{app_path}", file=sys.stderr)
        return 1

    threading.Thread(target=open_browser, args=(DEFAULT_PORT,), daemon=True).start()

    from streamlit.web import cli as stcli

    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        f"--server.port={DEFAULT_PORT}",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
    ]
    return stcli.main()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
