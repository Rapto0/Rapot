import hashlib
import importlib
import sys

import pytest


def _load_auth_module(monkeypatch, **env: str):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-32chars")
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("USER_PASSWORD", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)
    monkeypatch.delenv("USER_PASSWORD_HASH", raising=False)
    monkeypatch.delenv("ALLOW_INSECURE_JWT_SECRET", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("PYTHON_ENV", raising=False)

    for key, value in env.items():
        monkeypatch.setenv(key, value)

    sys.modules.pop("api.auth", None)
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


def test_placeholder_jwt_secret_is_rejected(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "REPLACE_WITH_STRONG_RANDOM_64_HEX_SECRET")

    sys.modules.pop("api.auth", None)
    with pytest.raises(RuntimeError, match="insecure placeholder"):
        import api.auth as auth_module

        importlib.reload(auth_module)


def test_insecure_jwt_fallback_is_blocked_outside_local_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "")
    monkeypatch.setenv("ALLOW_INSECURE_JWT_SECRET", "1")
    monkeypatch.setenv("APP_ENV", "production")

    sys.modules.pop("api.auth", None)
    with pytest.raises(RuntimeError, match="only allowed in local/development"):
        import api.auth as auth_module

        importlib.reload(auth_module)


def test_insecure_jwt_fallback_is_allowed_in_local_env(monkeypatch):
    module = _load_auth_module(
        monkeypatch,
        JWT_SECRET_KEY="",
        ALLOW_INSECURE_JWT_SECRET="1",
        APP_ENV="development",
    )

    assert module.SECRET_KEY == "dev-only-insecure-jwt-secret-change-me"
