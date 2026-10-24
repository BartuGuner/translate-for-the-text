"""Host, port and filesystem paths. Override with LEXIHOVER_PORT / LEXIHOVER_USERDATA."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "127.0.0.1"
PORT = int(os.environ.get("LEXIHOVER_PORT", "5057"))
DICTIONARY_DB = ROOT / "data" / "dictionary.db"
USERDATA_DIR = Path(os.environ.get("LEXIHOVER_USERDATA", ROOT / "userdata"))
USER_DB = USERDATA_DIR / "user.db"
MAX_TEXT_CHARS = 50_000
MAX_REQUEST_BYTES = 1_000_000
