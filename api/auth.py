"""
JWT Authentication Module
Token oluşturma, doğrulama ve kullanıcı yetkilendirme.

Kullanım:
    1. /auth/token endpoint'inden token alın
    2. Token'ı Authorization: Bearer <token> header'ında gönderin
"""

import hashlib

# ==================== CONFIGURATION ====================
import os
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

# Güvenlik ayarları - .env'den okunmalı
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-change-in-production-" + os.urandom(8).hex())
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 saat

# Varsayılan kullanıcı şifreleri - .env'den okunmalı
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
DEFAULT_USER_PASSWORD = os.getenv("USER_PASSWORD", "")

# Bearer token security
security = HTTPBearer(auto_error=False)


# ==================== PASSWORD HASHING ====================


def hash_password(password: str) -> str:
    """SHA256 ile şifre hash'leme."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Şifre doğrulama."""
    return hash_password(plain_password) == hashed_password


# ==================== SCHEMAS ====================


class Token(BaseModel):
    """Token yanıtı."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token içeriği."""

    username: str | None = None
    scopes: list[str] = []


class UserLogin(BaseModel):
    """Login isteği."""

    username: str
    password: str


class User(BaseModel):
    """Kullanıcı modeli."""

    username: str
    is_admin: bool = False
    disabled: bool = False


# ==================== USERS DATABASE ====================
# Production'da veritabanından alınmalı
# Şifreler .env'den okunur - eğer ayarlanmamışsa kullanıcı devre dışı


def _build_users_db() -> dict:
    """Kullanıcı veritabanını environment'tan oluşturur."""
    users = {}

    # Admin kullanıcı
    if DEFAULT_ADMIN_PASSWORD:
        users["admin"] = {
            "username": "admin",
            "hashed_password": hash_password(DEFAULT_ADMIN_PASSWORD),
            "is_admin": True,
            "disabled": False,
        }

    # Normal kullanıcı
    if DEFAULT_USER_PASSWORD:
        users["user"] = {
            "username": "user",
            "hashed_password": hash_password(DEFAULT_USER_PASSWORD),
            "is_admin": False,
            "disabled": False,
        }

    return users


USERS_DB = _build_users_db()


# ==================== HELPER FUNCTIONS ====================


def get_user(username: str) -> dict | None:
    """Kullanıcı bilgilerini döndürür."""
    return USERS_DB.get(username)


def authenticate_user(username: str, password: str) -> dict | None:
    """
    Kullanıcı doğrulama.

    Args:
        username: Kullanıcı adı
        password: Düz metin şifre

    Returns:
        Kullanıcı dict'i veya None
    """
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    JWT access token oluşturur.

    Args:
        data: Token'a eklenecek veri
        expires_delta: Geçerlilik süresi

    Returns:
        JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_token(token: str) -> TokenData | None:
    """
    JWT token doğrulama.

    Args:
        token: JWT token string

    Returns:
        TokenData veya None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return TokenData(username=username)
    except JWTError:
        return None


# ==================== DEPENDENCIES ====================


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """
    Mevcut kullanıcıyı döndürür.

    Dependency olarak kullanılır:
        @app.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            ...
    """
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

    if user.get("disabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kullanıcı devre dışı",
        )

    return User(
        username=user["username"],
        is_admin=user.get("is_admin", False),
        disabled=user.get("disabled", False),
    )


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Admin kullanıcı gerektiren dependency.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin yetkisi gerekli",
        )
    return current_user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User | None:
    """
    Opsiyonel kullanıcı kontrolü.

    Token yoksa veya geçersizse None döner, hata vermez.
    """
    if credentials is None:
        return None

    token = credentials.credentials
    token_data = verify_token(token)

    if token_data is None:
        return None

    user = get_user(token_data.username)
    if user is None or user.get("disabled"):
        return None

    return User(
        username=user["username"],
        is_admin=user.get("is_admin", False),
        disabled=user.get("disabled", False),
    )
