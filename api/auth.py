"""
JWT authentication helpers.

Usage:
    1. Obtain token from `/auth/token`
    2. Send `Authorization: Bearer <token>` on protected endpoints
"""

import hashlib
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from logger import get_logger
from settings import get_settings

try:
    import bcrypt
except Exception:  # pragma: no cover - optional import safety
    bcrypt = None

logger = get_logger(__name__)
get_settings.cache_clear()
runtime_settings = get_settings()


# ==================== CONFIGURATION ====================


def _resolve_runtime_env() -> str:
    return str(runtime_settings.app_env or "production").strip().lower()


def _is_unsafe_secret(secret_key: str) -> bool:
    normalized = secret_key.strip().lower()
    if not normalized:
        return True
    blocked_markers = (
        "change_me",
        "dev-only",
        "insecure",
        "example",
        "your_",
        "replace_with",
        "placeholder",
    )
    return any(marker in normalized for marker in blocked_markers)


def _resolve_secret_key() -> str:
    secret_key = str(runtime_settings.jwt_secret_key or "").strip()
    if secret_key:
        if _is_unsafe_secret(secret_key):
            raise RuntimeError(
                "JWT_SECRET_KEY appears to be an insecure placeholder. "
                "Set a strong unique secret for production."
            )
        return secret_key

    allow_insecure = bool(runtime_settings.allow_insecure_jwt_secret)
    runtime_env = _resolve_runtime_env()
    if allow_insecure and runtime_env in {"development", "dev", "local", "test", "testing"}:
        insecure_fallback = "dev-only-insecure-jwt-secret-change-me"
        logger.warning(
            "JWT_SECRET_KEY missing. Using insecure fallback secret in %s environment.",
            runtime_env,
        )
        return insecure_fallback
    if allow_insecure:
        raise RuntimeError(
            "ALLOW_INSECURE_JWT_SECRET is only allowed in local/development environments."
        )

    raise RuntimeError(
        "JWT_SECRET_KEY env var is required. "
        "Set ALLOW_INSECURE_JWT_SECRET=1 only for local development."
    )


SECRET_KEY = _resolve_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(runtime_settings.jwt_expire_minutes)

DEFAULT_ADMIN_PASSWORD = str(runtime_settings.admin_password or "")
DEFAULT_USER_PASSWORD = str(runtime_settings.user_password or "")
DEFAULT_ADMIN_PASSWORD_HASH = str(runtime_settings.admin_password_hash or "")
DEFAULT_USER_PASSWORD_HASH = str(runtime_settings.user_password_hash or "")

security = HTTPBearer(auto_error=False)


# ==================== PASSWORD HELPERS ====================


def _is_legacy_sha256_hash(value: str) -> bool:
    token = value.strip()
    if len(token) != 64:
        return False
    return all(ch in "0123456789abcdefABCDEF" for ch in token)


def _is_bcrypt_hash(value: str) -> bool:
    token = value.strip()
    return token.startswith("$2a$") or token.startswith("$2b$") or token.startswith("$2y$")


def _normalized_password_bytes(password: str) -> bytes:
    """
    Bcrypt only accepts up to 72 bytes.
    For longer passwords, hash first to keep deterministic verify/hash behavior.
    """
    raw = password.encode("utf-8")
    if len(raw) <= 72:
        return raw
    return hashlib.sha256(raw).hexdigest().encode("ascii")


def _require_bcrypt() -> None:
    if bcrypt is None:
        raise RuntimeError("bcrypt package is required for password hashing")


def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    _require_bcrypt()
    hashed = bcrypt.hashpw(_normalized_password_bytes(password), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify bcrypt hash with SHA256 fallback for legacy hashes."""
    if not hashed_password:
        return False

    if _is_bcrypt_hash(hashed_password) and bcrypt is not None:
        try:
            return bcrypt.checkpw(
                _normalized_password_bytes(plain_password),
                hashed_password.encode("utf-8"),
            )
        except ValueError:
            return False

    if _is_legacy_sha256_hash(hashed_password):
        legacy_hash = hashlib.sha256(plain_password.encode()).hexdigest()
        return legacy_hash == hashed_password.lower()

    return False


def _resolve_password_hash(raw_password: str, raw_password_hash: str) -> str:
    candidate_hash = raw_password_hash.strip()
    if candidate_hash:
        if _is_legacy_sha256_hash(candidate_hash):
            return candidate_hash.lower()
        if _is_bcrypt_hash(candidate_hash):
            return candidate_hash
        raise RuntimeError(
            "ADMIN_PASSWORD_HASH/USER_PASSWORD_HASH invalid. "
            "Use bcrypt hash or legacy 64-char SHA256 hex."
        )

    if raw_password.strip():
        return hash_password(raw_password)

    return ""


# ==================== SCHEMAS ====================


class Token(BaseModel):
    """Token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Decoded token payload."""

    username: str | None = None
    scopes: list[str] = Field(default_factory=list)


class UserLogin(BaseModel):
    """Login request."""

    username: str
    password: str


class User(BaseModel):
    """Authenticated user model."""

    username: str
    is_admin: bool = False
    disabled: bool = False


# ==================== USERS DATABASE ====================


def _build_users_db() -> dict:
    """Build users in memory from env variables."""
    users: dict[str, dict[str, object]] = {}

    admin_hash = _resolve_password_hash(DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_PASSWORD_HASH)
    if admin_hash:
        users["admin"] = {
            "username": "admin",
            "hashed_password": admin_hash,
            "is_admin": True,
            "disabled": False,
        }

    user_hash = _resolve_password_hash(DEFAULT_USER_PASSWORD, DEFAULT_USER_PASSWORD_HASH)
    if user_hash:
        users["user"] = {
            "username": "user",
            "hashed_password": user_hash,
            "is_admin": False,
            "disabled": False,
        }

    return users


USERS_DB = _build_users_db()


# ==================== HELPER FUNCTIONS ====================


def get_user(username: str) -> dict | None:
    """Return user details."""
    return USERS_DB.get(username)


def authenticate_user(username: str, password: str) -> dict | None:
    """Validate username/password and return user dict on success."""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, str(user["hashed_password"])):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> TokenData | None:
    """Validate JWT token and return token data."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            return None
        return TokenData(username=username)
    except JWTError:
        return None


# ==================== DEPENDENCIES ====================


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Return currently authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Geçersiz kimlik bilgileri",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    token = credentials.credentials
    token_data = verify_token(token)

    if token_data is None:
        raise credentials_exception

    user = get_user(token_data.username)
    if user is None:
        raise credentials_exception

    if bool(user.get("disabled")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kullanıcı devre dışı",
        )

    return User(
        username=str(user["username"]),
        is_admin=bool(user.get("is_admin", False)),
        disabled=bool(user.get("disabled", False)),
    )


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency requiring admin privileges."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin yetkisi gerekli",
        )
    return current_user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User | None:
    """Return user when token is valid; otherwise None."""
    if credentials is None:
        return None

    token = credentials.credentials
    token_data = verify_token(token)

    if token_data is None:
        return None

    user = get_user(token_data.username)
    if user is None or bool(user.get("disabled")):
        return None

    return User(
        username=str(user["username"]),
        is_admin=bool(user.get("is_admin", False)),
        disabled=bool(user.get("disabled", False)),
    )
