import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database as db
from reset_utils import reset_app_data
from app_paths import debug_tools_enabled


class ResetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'data/machines.db'
        self.qrs = self.root / 'qr_codes'
        self.backups = self.root / 'data/backups'
        db.initialize_db(self.path)
        db.save_field_name(self.path, db.get_fields(self.path)[0]['id'], 'Bookname')
        self.rid = db.create_record(self.path)
        db.save_record_value(self.path, self.rid, 1, 'Alice in Wonderland')
        db.save_record_qr(self.path, self.rid, 'REC-0001.png')
        self.qrs.mkdir()
        (self.qrs / 'REC-0001.png').write_bytes(b'QR image fixture')
        self.backups.mkdir()
        (self.backups / 'before-restore-fixture.zip').write_bytes(b'private backup fixture')

    def test_reset_clears_active_and_legacy_data_and_restarts_defaults(self):
        export = self.root / 'downloaded-backup.zip'
        export.write_bytes(b'keep downloaded backup')
        with sqlite3.connect(self.path) as connection:
            connection.executescript("""
                CREATE TABLE equipment(id INTEGER PRIMARY KEY, record_id TEXT, qr_filename TEXT);
                INSERT INTO equipment VALUES(1, 'REC-0099', NULL);
                CREATE TABLE equipment_custom_fields(equipment_id INTEGER REFERENCES equipment(id), field_name TEXT, field_value TEXT);
                INSERT INTO equipment_custom_fields VALUES(1, 'Bookname', 'Old data');
                CREATE TABLE field_settings(sort_order INTEGER, field_name TEXT);
                INSERT INTO field_settings VALUES(0, 'Old');
            """)
        self.assertEqual(reset_app_data(self.path, self.qrs, self.backups), [])
        db.initialize_db(self.path)
        self.assertEqual(db.get_records(self.path), [])
        self.assertEqual(len(db.get_fields(self.path)), 1)
        default = db.get_fields(self.path)[0]
        self.assertEqual((default['id'], default['field_name'], default['field_type'], default['date_format']),
                         (1, None, 'Text', 'DD/MM/YYYY'))
        self.assertFalse(self.qrs.exists())
        self.assertFalse(self.backups.exists())
        self.assertEqual(export.read_bytes(), b'keep downloaded backup')
        with sqlite3.connect(self.path) as connection:
            for name in ['equipment', 'equipment_custom_fields', 'field_settings', 'record_values']:
                self.assertEqual(connection.execute(f'SELECT count(*) FROM {name}').fetchone()[0], 0)
        self.assertEqual(db.create_record(self.path), 'REC-0001')
        reset_app_data(self.path, self.qrs, self.backups)
        self.assertEqual(db.get_records(self.path), [])

    def test_failed_database_reset_restores_files_and_records(self):
        before = db.get_records(self.path)
        with sqlite3.connect(self.path) as connection:
            connection.execute("CREATE TRIGGER refuse_reset BEFORE DELETE ON custom_fields BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            reset_app_data(self.path, self.qrs, self.backups)
        self.assertEqual(db.get_records(self.path), before)
        self.assertTrue((self.qrs / 'REC-0001.png').is_file())
        self.assertTrue((self.backups / 'before-restore-fixture.zip').is_file())
        self.assertFalse(list(self.root.rglob('.itemori-reset-*')))

    def test_cleanup_failure_is_reported_after_committed_reset(self):
        with patch('reset_utils.shutil.rmtree', side_effect=PermissionError('test failure')):
            remaining = reset_app_data(self.path, self.qrs, self.backups)
        self.assertEqual(db.get_records(self.path), [])
        self.assertEqual(len(remaining), 2)
        self.assertTrue(all(path.exists() for path in remaining))

    def test_debug_tools_are_opt_in_and_never_enabled_in_release(self):
        with patch.dict('os.environ', {'ITEMORI_DEBUG': '0'}), patch('sys.frozen', False, create=True):
            self.assertFalse(debug_tools_enabled())
        with patch.dict('os.environ', {'ITEMORI_DEBUG': '1'}), patch('sys.frozen', False, create=True), patch('app_paths.Path.is_file', return_value=True):
            self.assertTrue(debug_tools_enabled())
        with patch.dict('os.environ', {'ITEMORI_DEBUG': '1'}), patch('sys.frozen', True, create=True):
            self.assertFalse(debug_tools_enabled())

    def test_public_source_hides_debug_tools_when_private_files_are_missing(self):
        with patch.dict('os.environ', {'ITEMORI_DEBUG': '1'}), patch('sys.frozen', False, create=True), patch('app_paths.Path.is_file', return_value=False):
            self.assertFalse(debug_tools_enabled())


if __name__ == '__main__':
    unittest.main()
