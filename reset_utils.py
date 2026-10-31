"""Reset the active collection and app-owned files after UI confirmation."""
from contextlib import closing
from pathlib import Path
import shutil
from uuid import uuid4

from database import get_connection


def reset_app_data(db_path: Path, qr_dir: Path, safety_dir: Path) -> list[Path]:
    """Return any old file folders that could not be removed after the reset.

    Keep the database schema/migration markers, reset its content in one
    transaction, and move owned files aside so failures before commit can undo
    the move. Downloaded/exported files outside these folders are not touched.
    """
    folders = (qr_dir, safety_dir)
    for folder in folders:
        if folder.is_symlink() or db_path.resolve().is_relative_to(folder.resolve()):
            raise ValueError("The reset folder is not a safe app data folder.")
    if qr_dir.resolve().is_relative_to(safety_dir.resolve()) or safety_dir.resolve().is_relative_to(qr_dir.resolve()):
        raise ValueError("Reset folders must be separate.")
    moved = []
    try:
        with closing(get_connection(db_path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            for folder in folders:
                if folder.exists():
                    staged = folder.with_name(f".itemori-reset-{uuid4().hex}-{folder.name}")
                    folder.rename(staged)
                    moved.append((folder, staged))
            connection.execute("DELETE FROM record_values")
            connection.execute("DELETE FROM records")
            connection.execute("DELETE FROM custom_fields")
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            # Imported legacy rows must not remain as hidden copies of user data.
            for table in ("equipment_custom_fields", "equipment", "field_settings"):
                if table in tables:
                    connection.execute(f'DELETE FROM "{table}"')
            connection.execute("DELETE FROM sqlite_sequence WHERE name IN ('records', 'custom_fields', 'equipment', 'equipment_custom_fields', 'field_settings')")
            connection.execute("INSERT INTO custom_fields (sort_order) VALUES (0)")
    except Exception:
        for folder, staged in reversed(moved):
            staged.rename(folder)
        raise
    remaining = []
    for _, staged in moved:
        try:
            shutil.rmtree(staged)
        except OSError:
            remaining.append(staged)
    return remaining
