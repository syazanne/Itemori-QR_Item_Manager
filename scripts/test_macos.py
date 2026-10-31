"""Exercise the actual bundled app with disposable records and native downloads."""
from __future__ import annotations

import json
import base64
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import database
from backup_utils import read_backup
from pypdf import PdfReader
from PIL import Image
from build_macos import ARCHIVE_NAME


def main():
    with tempfile.TemporaryDirectory(prefix="qr-desktop-test-") as folder:
        root = Path(folder)
        db = root / "data/machines.db"
        database.initialize_db(db)
        field = database.get_fields(db)[0]["id"]
        database.save_field_name(db, field, "Item")
        record = database.create_record(db)
        database.save_record_value(db, record, field, "Before desktop edit")
        downloads = root / "downloads"
        downloads.mkdir()
        result = root / "result.txt"
        env = dict(os.environ, QR_ITEM_MANAGER_DATA_DIR=str(root), ITEMORI_DEBUG="1",
                   QR_ITEM_MANAGER_TEST_SCRIPT=str(ROOT / "tests/desktop_smoke.js"),
                   QR_ITEM_MANAGER_TEST_RESULT=str(result),
                   QR_ITEM_MANAGER_TEST_DOWNLOADS=str(downloads),
                   QR_ITEM_MANAGER_TEST_PRINT=str(root / "printed-label.pdf"),
                   QR_ITEM_MANAGER_TEST_QUERY="record_id=REC-0001")
        # Test the downloadable archive outside iCloud-managed Desktop folders,
        # which may add FinderInfo attributes after signing.
        subprocess.run(["ditto", "-x", "-k", str(ROOT / "app" / ARCHIVE_NAME), str(root / "application")], check=True)
        app = root / "application/Itemori.app"
        subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
        executable = app / "Contents/MacOS/Itemori"
        with (root / "native.log").open("w") as log:
            process = subprocess.Popen([str(executable)], env=env, stdout=log, stderr=log, start_new_session=True)
            try:
                process.wait(timeout=180)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise RuntimeError("Desktop test timed out.\n" + (root / "desktop.log").read_text())
        evidence = ROOT / "build/desktop-test"
        evidence.mkdir(parents=True, exist_ok=True)
        for path in (result, Path(str(result) + ".png"), root / "desktop.log", root / "native.log", root / "printed-label.pdf"):
            if path.is_file():
                (evidence / path.name).write_bytes(path.read_bytes())
        if not result.is_file():
            raise RuntimeError("App did not produce a result. See build/desktop-test logs.")
        text = result.read_text()
        if text.startswith("ERROR"):
            raise RuntimeError(text)
        outcome = json.loads(text)
        assert outcome["ok"], outcome
        assert database.get_record(db, record)["values"][field] == "Offline desktop test"
        with Image.open(next(downloads.glob("*.png"))) as image:
            image.verify()
        assert len(PdfReader(str(next(downloads.glob("*.pdf")))).pages) == 1
        printed = PdfReader(str(root / "printed-label.pdf"))
        assert len(printed.pages) == 1
        assert record in printed.pages[0].extract_text()
        snapshot = read_backup(next(downloads.glob("*.zip")).read_bytes())
        assert snapshot["records"][0]["record_id"] == record
        # Reopen the same collection, then upload and restore the downloaded ZIP.
        smoke = (ROOT / "tests/desktop_smoke.js").read_text()
        helpers = smoke.split("await waitFor(() => keyed('value_REC-0001_1')", 1)[0]
        restore_script = root / "restore.js"
        backup_b64 = base64.b64encode(next(downloads.glob("*.zip")).read_bytes()).decode("ascii")
        fixture = "const backupBytes = Uint8Array.from(atob(" + json.dumps(backup_b64) + "), c => c.charCodeAt(0));\n"
        restore_script.write_text(fixture + helpers + (ROOT / "tests/desktop_restore.js").read_text())
        restore_result = root / "restore-result.txt"
        env.update(QR_ITEM_MANAGER_TEST_SCRIPT=str(restore_script),
                   QR_ITEM_MANAGER_TEST_RESULT=str(restore_result))
        with (root / "native-restore.log").open("w") as log:
            process = subprocess.Popen([str(executable)], env=env, stdout=log, stderr=log, start_new_session=True)
            try:
                process.wait(timeout=90)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise RuntimeError("Native restore test timed out")
        text_restore = restore_result.read_text() if restore_result.is_file() else "ERROR: missing restore result"
        (evidence / "restore-result.txt").write_text(text_restore)
        if text_restore.startswith("ERROR"):
            raise RuntimeError(text_restore)
        assert json.loads(text_restore)["restore"]
        assert list((root / "data/backups").glob("before-restore-*.zip"))
        assert database.get_record(db, record)["values"][field] == "Offline desktop test"
        # Release reset is exercised only after restore/persistence checks, and
        # only against the temporary collection created by this runner.
        reset_script = root / "reset.js"
        reset_script.write_text(helpers + (ROOT / "tests/desktop_reset.js").read_text())
        reset_result = root / "reset-result.txt"
        env.update(QR_ITEM_MANAGER_TEST_SCRIPT=str(reset_script), QR_ITEM_MANAGER_TEST_RESULT=str(reset_result))
        with (root / "native-reset.log").open("w") as log:
            process = subprocess.Popen([str(executable)], env=env, stdout=log, stderr=log, start_new_session=True)
            try:
                process.wait(timeout=90)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise RuntimeError("Native reset test timed out")
        reset_text = reset_result.read_text() if reset_result.is_file() else "ERROR: missing reset result"
        (evidence / "reset-result.txt").write_text(reset_text)
        for artifact in (Path(str(reset_result) + ".png"), root / "native-reset.log"):
            if artifact.is_file():
                (evidence / artifact.name).write_bytes(artifact.read_bytes())
        if reset_text.startswith("ERROR"):
            raise RuntimeError(reset_text)
        assert json.loads(reset_text)["reset"]
        assert database.get_records(db) == []
        assert len(database.get_fields(db)) == 1 and database.get_fields(db)[0]["field_name"] is None
        assert not (root / "qr_codes").exists()
        assert not (root / "data/backups").exists()
        assert list(downloads.glob("*.zip")), "Downloaded backup must be kept"
        assert not (app / "Contents/Resources/backend/_internal/camera_reading_frontend").exists()
        print("PASS: native startup, editing, QR, printing, downloads, hidden debug tools, help, restart, restore and confirmed reset")
        print(text)


if __name__ == "__main__":
    main()
