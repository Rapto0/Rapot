import time
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from api.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
    Token,
    User,
    UserLogin,
    authenticate_user,
    create_access_token,
    create_ws_ticket,
    decode_session_token,
    generate_csrf_token,
    get_current_user,
    get_user,
    is_secure_cookie_request,
    verify_csrf_double_submit,
)
from api.private_data_access import require_admin_request
from api.rate_limit import limiter

router = APIRouter(tags=["Authentication"])


class SessionStatusResponse(BaseModel):
    authenticated: bool
    user: User | None = None
    expires_in: int | None = None
    expires_at: float | None = None


class LogoutResponse(BaseModel):
    logged_out: bool = True


class WsTicketResponse(BaseModel):
    ticket: str
    expires_in: int


def _set_session_cookies(
    response: Response,
    request: Request,
    access_token: str,
    max_age: int,
    csrf_token: str | None = None,
) -> None:
    secure = is_secure_cookie_request(request)
    csrf = csrf_token or generate_csrf_token()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=access_token,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf,
        max_age=max_age,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )


def _clear_session_cookies(response: Response, request: Request) -> None:
    secure = is_secure_cookie_request(request)
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=secure,
        samesite="lax",
    )
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path="/",
        httponly=False,
        secure=secure,
        samesite="lax",
    )


def _extract_bearer(request: Request) -> str | None:
    auth_header = request.headers.get("authorization")
    if not auth_header:
        return None
    scheme, separator, token = auth_header.partition(" ")
    if separator and scheme.lower() == "bearer" and token.strip():
        return token.strip()
    return None


@router.post("/auth/token", response_model=Token)
@limiter.limit("5/minute")
async def login(request: Request, user_login: UserLogin):
    user = authenticate_user(user_login.username, user_login.password)
    if not user or user.get("disabled"):
        raise HTTPException(
            status_code=401,
            detail="Kullanici adi veya sifre hatali",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/auth/session", response_model=SessionStatusResponse)
@limiter.limit("5/minute")
async def create_session(request: Request, response: Response, user_login: UserLogin):
    user = authenticate_user(user_login.username, user_login.password)
    if not user or user.get("disabled"):
        raise HTTPException(
            status_code=401,
            detail="Kullanıcı adı veya şifre hatalı.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(seconds=expires_in),
    )
    _set_session_cookies(response, request, access_token, expires_in)
    return SessionStatusResponse(
        authenticated=True,
        user=User(
            username=str(user["username"]),
            is_admin=bool(user.get("is_admin", False)),
            disabled=bool(user.get("disabled", False)),
        ),
        expires_in=expires_in,
        expires_at=time.time() + expires_in,
    )


@router.get("/auth/session", response_model=SessionStatusResponse)
async def get_session_status(request: Request, response: Response):
    bearer = _extract_bearer(request)
    cookie_token = None if bearer else request.cookies.get(SESSION_COOKIE_NAME)
    token = bearer or cookie_token
    if not token:
        return SessionStatusResponse(authenticated=False)

    decoded = decode_session_token(token)
    if decoded is None:
        if cookie_token:
            _clear_session_cookies(response, request)
        return SessionStatusResponse(authenticated=False)

    username, expires_at = decoded
    user = get_user(username)
    if user is None or bool(user.get("disabled")):
        if cookie_token:
            _clear_session_cookies(response, request)
        return SessionStatusResponse(authenticated=False)

    expires_in = max(1, int(expires_at - time.time()))
    if cookie_token and not request.cookies.get(CSRF_COOKIE_NAME):
        response.set_cookie(
            key=CSRF_COOKIE_NAME,
            value=generate_csrf_token(),
            max_age=expires_in,
            httponly=False,
            secure=is_secure_cookie_request(request),
            samesite="lax",
            path="/",
        )

    return SessionStatusResponse(
        authenticated=True,
        user=User(
            username=str(user["username"]),
            is_admin=bool(user.get("is_admin", False)),
            disabled=bool(user.get("disabled", False)),
        ),
        expires_in=expires_in,
        expires_at=expires_at,
    )


@router.post("/auth/logout", response_model=LogoutResponse)
async def logout(request: Request, response: Response):
    if (
        _extract_bearer(request) is None
        and request.cookies.get(SESSION_COOKIE_NAME)
        and not verify_csrf_double_submit(
            request.cookies.get(CSRF_COOKIE_NAME),
            request.headers.get(CSRF_HEADER_NAME),
        )
    ):
        raise HTTPException(
            status_code=403,
            detail="CSRF doğrulaması başarısız.",
        )
    _clear_session_cookies(response, request)
    return LogoutResponse(logged_out=True)


@router.post("/auth/ws-ticket", response_model=WsTicketResponse)
@limiter.limit("30/minute")
async def issue_ws_ticket(request: Request):
    grant = getattr(request.state, "private_data_grant", None) or require_admin_request(request)
    try:
        ticket, expires_in = create_ws_ticket(grant.username, grant.expires_at)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Yönetici oturumu geçersiz veya süresi dolmuş.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    return WsTicketResponse(ticket=ticket, expires_in=expires_in)


@router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
