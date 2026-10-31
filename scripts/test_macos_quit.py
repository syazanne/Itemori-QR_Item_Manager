"""Exercise Escape and the real native quit dialog using a disposable page."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import subprocess
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    output = ROOT / "build/quit-test"
    output.mkdir(parents=True, exist_ok=True)
    executable = output / "ItemoriQuitTests"
    env = dict(os.environ, CLANG_MODULE_CACHE_PATH=str(ROOT / "build/clang-cache"))
    subprocess.run(["xcrun", "swiftc", "-parse-as-library", "-swift-version", "5", "-DQUIT_TESTING",
                    "-target", "arm64-apple-macosx14.0", str(ROOT / "desktop/Itemori.swift"),
                    str(ROOT / "desktop/LabelPrinting.swift"), str(ROOT / "tests/native_quit.swift"),
                    "-o", str(executable), "-framework", "Cocoa", "-framework", "WebKit", "-framework", "PDFKit"],
                   check=True, env=env)
    with tempfile.TemporaryDirectory(prefix="itemori-quit-fixture-") as folder:
        root = Path(folder)
        (root / "index.html").write_text('<!doctype html><input id="draft"><iframe src="frame.html"></iframe>')
        (root / "frame.html").write_text('<!doctype html><input id="inside" placeholder="Component input">')
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=folder))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        result = output / "result.txt"
        result.unlink(missing_ok=True)
        env.update(QUIT_TEST_URL=f"http://127.0.0.1:{server.server_port}/", QUIT_TEST_RESULT=str(result))
        try:
            subprocess.run([str(executable)], env=env, check=True, timeout=60)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
        evidence = result.read_text()
        assert evidence.startswith("PASS"), evidence
        print(evidence)


if __name__ == "__main__":
    main()
