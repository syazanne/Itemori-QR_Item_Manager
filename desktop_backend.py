"""Private local server owned by the macOS application."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import sys
import threading
import time


def watch_parent(parent_pid: int) -> None:
    while True:
        if os.getppid() != parent_pid:
            os._exit(0)
        time.sleep(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ready-file", required=True, type=Path)
    parser.add_argument("--parent-pid", type=int)
    options = parser.parse_args()
    from app_paths import writable_root
    root = Path(__file__).resolve().parent
    data = writable_root(root)
    data.mkdir(parents=True, exist_ok=True)
    os.environ["QR_ITEM_MANAGER_DATA_DIR"] = str(data)
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
    # Avoid loading a config from the folder from which Finder launched us.
    os.chdir(root)
    if options.parent_pid:
        threading.Thread(target=watch_parent, args=(options.parent_pid,), daemon=True).start()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    ready = options.ready_file.resolve()
    ready.parent.mkdir(parents=True, exist_ok=True)
    temporary = ready.with_suffix(".tmp")
    temporary.write_text(json.dumps({"port": port, "pid": os.getpid()}))
    temporary.replace(ready)
    from streamlit.web import bootstrap
    flags = {
        "server.address": "127.0.0.1", "server.port": port,
        "server.headless": True, "server.fileWatcherType": "none",
        "server.runOnSave": False, "server.maxUploadSize": 100,
        "browser.gatherUsageStats": False, "browser.serverAddress": "127.0.0.1",
        "browser.serverPort": port, "global.developmentMode": False,
        "client.toolbarMode": "minimal", "server.enableCORS": True,
        "server.enableXsrfProtection": True,
    }
    bootstrap.load_config_options(flags)
    bootstrap.run(str(root / "app.py"), False, [], flags)


if __name__ == "__main__":
    main()
