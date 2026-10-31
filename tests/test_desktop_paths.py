import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from app_paths import writable_root
import scanner


class DesktopStorageTests(unittest.TestCase):
    def test_source_checkout_keeps_its_existing_data_location(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, "frozen", False, create=True):
            self.assertEqual(writable_root(Path("/source")), Path("/source"))

    def test_installed_app_uses_application_support(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, "frozen", True, create=True):
            root = writable_root(Path("/Applications/Itemori.app/Contents/Resources"))
            self.assertEqual(root, Path.home() / "Library/Application Support/QR Item Manager")

    def test_scanner_writes_only_into_separate_user_data(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"QR_ITEM_MANAGER_DATA_DIR": folder}):
                with patch.object(scanner.components, "declare_component") as declare:
                    scanner.qrcode_scanner()
                    bundle = Path(folder).resolve() / "data/scanner_component_jsqr"
                    declare.assert_called_once_with("qr_camera_jsqr", path=str(bundle))
                    self.assertTrue((bundle / "vendor/jsQR.js").is_file())
                    self.assertTrue((bundle / "index.html").is_file())


if __name__ == "__main__":
    unittest.main()
