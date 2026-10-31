"""Keep installed app resources separate from the user's writable records."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def debug_tools_enabled() -> bool:
    """Experiments are opt-in in source checkouts, never in the release app."""
    if getattr(sys, "frozen", False) or os.environ.get("ITEMORI_DEBUG") != "1":
        return False
    root = Path(__file__).resolve().parent
    return (root / "camera_reading.py").is_file() and (root / "camera_reading_frontend/index.html").is_file()


def writable_root(source_root: Path) -> Path:
    override = os.environ.get("QR_ITEM_MANAGER_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if getattr(sys, "frozen", False):
        # Keep the original storage location when the app is renamed to Itemori.
        return Path.home() / "Library" / "Application Support" / "QR Item Manager"
    return source_root
