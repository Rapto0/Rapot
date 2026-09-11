"""JWT wire compatibility and fail-closed validation, without external services."""

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest

TEST_KEY = "rapot-legacy-jwt-test-key-not-a-secret-64-bytes-long-only-for-tests"
NOW = 1_800_000_000
LEGACY_PAYLOAD = {"sub": "legacy-user", "exp": 4_102_444_800}
# Generated and decoded with python-jose 3.5.0 before its removal, using TEST_KEY above.
LEGACY_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiJsZWdhY3ktdXNlciIsImV4cCI6NDEwMjQ0NDgwMH0."
    "hce5sFMH5QKUJNLVLo_XvTukpVE-UIusdcXU9uCJvG4"
)


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _token(payload: object, *, algorithm: str = "HS256", key: str = TEST_KEY) -> str:
    """Build independent compact tokens, including deliberately mislabeled algorithms."""
    header = _b64(json.dumps({"alg": algorithm, "typ": "JWT"}).encode())
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header}.{body}"
    digest = hashlib.sha384 if algorithm == "HS384" else hashlib.sha256
    signature = (
        b"" if algorithm == "none" else hmac.digest(key.encode(), signing_input.encode(), digest)
    )
    return f"{signing_input}.{_b64(signature)}"


@pytest.fixture
def auth(api_auth_users, monkeypatch):
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls.fromtimestamp(NOW, tz)

    # Routes can retain the original auth module after separate import/reload tests.
    auth_globals = api_auth_users.create_access_token.__globals__
    monkeypatch.setitem(auth_globals, "SECRET_KEY", TEST_KEY)
    monkeypatch.setitem(auth_globals, "datetime", FrozenDatetime)
    monkeypatch.setattr(jwt.api_jwt, "datetime", FrozenDatetime)
    return SimpleNamespace(
        create_access_token=auth_globals["create_access_token"],
        verify_token=auth_globals["verify_token"],
    )


def test_legacy_jose_token_is_accepted(auth):
    assert jwt.decode(LEGACY_TOKEN, TEST_KEY, algorithms=["HS256"]) == LEGACY_PAYLOAD
    assert auth.verify_token(LEGACY_TOKEN).username == "legacy-user"


def test_new_tokens_keep_compact_hs256_signature_and_expiry(auth):
    claims = {"sub": "user"}
    token = auth.create_access_token(claims, timedelta(minutes=5))
    header, payload, signature = token.split(".")
    assert json.loads(base64.urlsafe_b64decode(header + "==")) == {
        "alg": "HS256",
        "typ": "JWT",
    }
    assert json.loads(base64.urlsafe_b64decode(payload + "==")) == {
        "sub": "user",
        "exp": NOW + 300,
    }
    expected = hmac.digest(TEST_KEY.encode(), f"{header}.{payload}".encode(), "sha256")
    assert hmac.compare_digest(signature, _b64(expected))
    assert claims == {"sub": "user"}
    assert auth.verify_token(token).username == "user"


def test_tampered_payload_cannot_promote_user(auth):
    token = _token({"sub": "user", "exp": NOW + 60})
    header, _, signature = token.split(".")
    tampered = _b64(json.dumps({"sub": "admin", "exp": NOW + 60}).encode())
    assert auth.verify_token(f"{header}.{tampered}.{signature}") is None


def test_wrong_signature_is_rejected(auth):
    assert auth.verify_token(_token(LEGACY_PAYLOAD, key="another-clearly-fake-test-key")) is None


@pytest.mark.parametrize("algorithm", ["none", "HS384", "RS256", "ES256"])
def test_token_header_cannot_select_another_algorithm(auth, algorithm):
    token = _token(LEGACY_PAYLOAD, algorithm=algorithm)
    if algorithm == "HS384":
        # This token really verifies with the same secret under the other HMAC algorithm.
        assert jwt.decode(token, TEST_KEY, algorithms=["HS384"]) == LEGACY_PAYLOAD
    # RS/ES inputs model an attacker relabeling an HMAC token as an asymmetric token.
    assert auth.verify_token(token) is None


def test_exp_is_required(auth):
    assert auth.verify_token(_token({"sub": "user"})) is None


@pytest.mark.parametrize("exp", [None, "not-a-date", [], {}, float("inf"), float("nan")])
def test_malformed_expiry_is_rejected_without_raising(auth, exp):
    assert auth.verify_token(_token({"sub": "user", "exp": exp})) is None


@pytest.mark.parametrize("subject", [None, 123, True, [], {}])
def test_subject_must_be_a_string(auth, subject):
    assert auth.verify_token(_token({"sub": subject, "exp": NOW + 60})) is None


def test_subject_is_required(auth):
    assert auth.verify_token(_token({"exp": NOW + 60})) is None


@pytest.mark.parametrize("seconds,valid", [(-1, False), (0, False), (1, True)])
def test_expiry_boundary_has_no_implicit_leeway(auth, seconds, valid):
    result = auth.verify_token(_token({"sub": "user", "exp": NOW + seconds}))
    assert (result is not None) is valid


@pytest.mark.parametrize("claim", ["iat", "nbf"])
def test_future_time_claims_are_rejected(auth, claim):
    assert auth.verify_token(_token({**LEGACY_PAYLOAD, claim: NOW + 60})) is None


@pytest.mark.parametrize("payload", [[], "user", None])
def test_non_object_payload_is_rejected(auth, payload):
    assert auth.verify_token(_token(payload)) is None


@pytest.mark.parametrize("token", ["", "not-a-token", "a.b.c", "e30.e30."])
def test_malformed_compact_tokens_are_rejected(auth, token):
    assert auth.verify_token(token) is None


def test_legacy_numeric_string_expiry_remains_supported(auth):
    assert auth.verify_token(_token({"sub": "user", "exp": str(NOW + 60)})).username == "user"
