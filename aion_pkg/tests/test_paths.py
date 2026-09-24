"""Where AION keeps its signing keys and store (and how <= 2.3.2 is migrated)."""

from aion import paths


def test_home_defaults_to_user_home(monkeypatch):
    monkeypatch.delenv("AION_HOME", raising=False)
    assert paths.home().name == ".aion"


def test_home_override(monkeypatch, tmp_path):
    monkeypatch.setenv("AION_HOME", str(tmp_path / "aion-home"))
    assert paths.home() == tmp_path / "aion-home"
    assert paths.key_dir() == tmp_path / "aion-home" / "keys"
    assert paths.db_file() == tmp_path / "aion-home" / "aion.db"


def test_explicit_key_dir_and_db_path(monkeypatch, tmp_path):
    monkeypatch.setenv("AION_KEY_DIR", str(tmp_path / "keys"))
    monkeypatch.setenv("AION_DB_PATH", str(tmp_path / "db" / "store.db"))
    assert paths.key_dir() == tmp_path / "keys"
    assert paths.db_file() == tmp_path / "db" / "store.db"


def test_key_file_creates_its_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("AION_HOME", str(tmp_path / "home"))
    path = paths.key_file()
    assert path.parent.is_dir()
    assert path.name == "aion_private_key.pem"


def test_legacy_install_is_migrated_once(monkeypatch, tmp_path):
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "aion_private_key.pem").write_text("private-key", encoding="utf-8")
    (legacy / "aion_public_key.pem").write_text("public-key", encoding="utf-8")
    (legacy / "aion.db").write_text("db", encoding="utf-8")

    monkeypatch.setenv("AION_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(paths, "legacy_dir", lambda: legacy)
    paths._MIGRATED.clear()

    migrated = paths.migrate_legacy(quiet=True)
    assert sorted(migrated) == [
        "aion.db",
        "aion_private_key.pem",
        "aion_public_key.pem",
    ]
    assert (paths.key_dir() / "aion_private_key.pem").read_text(encoding="utf-8") == "private-key"
    assert paths.db_file().read_text(encoding="utf-8") == "db"

    # Idempotent: the second pass has nothing left to do.
    assert paths.migrate_legacy(quiet=True) == []


def test_migration_never_overwrites_an_existing_identity(monkeypatch, tmp_path):
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "aion_private_key.pem").write_text("old", encoding="utf-8")

    monkeypatch.setenv("AION_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(paths, "legacy_dir", lambda: legacy)
    paths._MIGRATED.clear()

    paths.key_dir().mkdir(parents=True, exist_ok=True)
    (paths.key_dir() / "aion_private_key.pem").write_text("new", encoding="utf-8")

    paths.migrate_legacy(quiet=True)
    assert (paths.key_dir() / "aion_private_key.pem").read_text(encoding="utf-8") == "new"
