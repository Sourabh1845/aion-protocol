"""Where AION keeps its signing keys and local store.

Default home: ``~/.aion`` - one identity per user that survives pip upgrades.

Until 2.3.2 these files were written next to the installed package
(``site-packages/storage/``), which meant a reinstall could destroy a user's
signing identity - and every previously issued token with it. Legacy files are
migrated once, automatically, into the new home.

Overrides are resolved on every call (not cached) so tests and hosted
deployments can steer them at runtime:

    AION_HOME      base directory for keys + store   (default: ~/.aion)
    AION_KEY_DIR   signing keys only                 (default: <home>/keys)
    AION_DB_PATH   sqlite store only                 (default: <home>/aion.db)
"""

import os
import shutil
from pathlib import Path

KEY_FILES = ("aion_private_key.pem", "aion_public_key.pem")

_MIGRATED = set()


def home():
    override = os.environ.get("AION_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".aion"


def key_dir():
    override = os.environ.get("AION_KEY_DIR")
    if override:
        return Path(override).expanduser()
    return home() / "keys"


def db_file():
    override = os.environ.get("AION_DB_PATH")
    if override:
        return Path(override).expanduser()
    return home() / "aion.db"


def legacy_dir():
    """Where <= 2.3.2 wrote keys and the sqlite store (next to the package)."""
    return Path(__file__).resolve().parent.parent / "storage"


def _copy_missing(src, dst):
    if not src.exists() or dst.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def migrate_legacy(quiet=False):
    """Pull a pre-2.3.3 install's identity into the new home. Idempotent."""
    legacy = legacy_dir()
    try:
        already = str(legacy.resolve()) == str(home().resolve())
    except OSError:
        already = False
    if already:
        return []

    marker = (str(legacy), str(home()), str(key_dir()), str(db_file()))
    if marker in _MIGRATED:
        return []
    _MIGRATED.add(marker)

    migrated = []
    for name in KEY_FILES:
        if _copy_missing(legacy / name, key_dir() / name):
            migrated.append(name)
    if _copy_missing(legacy / "aion.db", db_file()):
        migrated.append("aion.db")

    if migrated and not quiet:
        print(
            f"AION: migrated {len(migrated)} file(s) from the old install dir "
            f"into {home()} (set AION_HOME to change that location)"
        )
    return migrated


def key_file(name="aion_private_key.pem"):
    """Resolved key path; triggers legacy migration and creates the directory."""
    migrate_legacy()
    directory = key_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory / name
