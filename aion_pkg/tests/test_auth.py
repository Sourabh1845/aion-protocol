"""Auth middleware behaviour: keys fail closed, dev key needs explicit opt-in."""

import pytest

pytest.importorskip("fastapi", reason="cloud extra (fastapi) not installed")

from fastapi import HTTPException  # noqa: E402

from aion.auth_middleware import DEV_KEY, get_api_key  # noqa: E402


def test_configured_key_wins(monkeypatch):
    monkeypatch.setenv("AION_API_KEY", "prod-key-under-test")
    monkeypatch.delenv("AION_ALLOW_DEV_KEY", raising=False)
    assert get_api_key() == "prod-key-under-test"


def test_unconfigured_server_fails_closed(monkeypatch):
    monkeypatch.delenv("AION_API_KEY", raising=False)
    monkeypatch.delenv("AION_ALLOW_DEV_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        get_api_key()
    assert exc.value.status_code == 503


def test_dev_key_requires_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("AION_API_KEY", raising=False)
    monkeypatch.setenv("AION_ALLOW_DEV_KEY", "1")
    assert get_api_key() == DEV_KEY


def test_well_known_dev_key_is_not_an_implicit_fallback(monkeypatch):
    """The dev key lives in this repo, so it must never be accepted by default."""
    monkeypatch.delenv("AION_API_KEY", raising=False)
    monkeypatch.delenv("AION_ALLOW_DEV_KEY", raising=False)
    with pytest.raises(HTTPException):
        get_api_key()
