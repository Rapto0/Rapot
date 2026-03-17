import hashlib
import importlib

import pytest


def _load_auth_module(monkeypatch, **env: str):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("USER_PASSWORD", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)
    monkeypatch.delenv("USER_PASSWORD_HASH", raising=False)

    for key, value in env.items():
        monkeypatch.setenv(key, value)

    import api.auth as auth_module

    return importlib.reload(auth_module)


def test_hash_password_uses_bcrypt(monkeypatch):
    auth_module = _load_auth_module(monkeypatch)

    hashed = auth_module.hash_password("secret123")
    assert hashed.startswith("$2")
    assert hashed != hashlib.sha256(b"secret123").hexdigest()
    assert auth_module.verify_password("secret123", hashed)


def test_verify_password_supports_legacy_sha256(monkeypatch):
    auth_module = _load_auth_module(monkeypatch)

    legacy_hash = hashlib.sha256(b"legacy-pass").hexdigest()
    assert auth_module.verify_password("legacy-pass", legacy_hash)
    assert not auth_module.verify_password("wrong-pass", legacy_hash)


def test_invalid_password_hash_env_raises(monkeypatch):
    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD_HASH/USER_PASSWORD_HASH invalid"):
        _load_auth_module(monkeypatch, ADMIN_PASSWORD_HASH="not-a-valid-hash")
