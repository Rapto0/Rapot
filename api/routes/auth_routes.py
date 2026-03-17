from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request

from api.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    Token,
    User,
    UserLogin,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from api.rate_limit import limiter

router = APIRouter(tags=["Authentication"])


@router.post("/auth/token", response_model=Token)
@limiter.limit("5/minute")
async def login(request: Request, user_login: UserLogin):
    user = authenticate_user(user_login.username, user_login.password)
    if not user:
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


@router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
