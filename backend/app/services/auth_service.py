"""
Authentication service: register, login, token refresh, and current user retrieval.
"""

from __future__ import annotations

from uuid import UUID
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AlreadyExistsError, AuthenticationError, NotFoundError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

logger = get_logger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, data: UserRegisterRequest) -> UserResponse:
        # Check email uniqueness
        existing_email = await self.db.execute(
            select(User).where(User.email == data.email)
        )
        if existing_email.scalar_one_or_none():
            raise AlreadyExistsError("A user with this email already exists.")

        # Check username uniqueness
        existing_username = await self.db.execute(
            select(User).where(User.username == data.username)
        )
        if existing_username.scalar_one_or_none():
            raise AlreadyExistsError("This username is already taken.")

        user = User(
            email=data.email,
            username=data.username,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            is_active=True,
            is_verified=False,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        logger.info("User registered", user_id=str(user.id), email=user.email)
        return UserResponse.model_validate(user)

    async def login(self, data: UserLoginRequest) -> TokenResponse:
        result = await self.db.execute(
            select(User).where(User.email == data.email)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            raise AuthenticationError("This account has been deactivated.")

        access_token = create_access_token(user.id, user.email)
        refresh_token = create_refresh_token(user.id)

        from app.core.config import settings
        logger.info("User logged in", user_id=str(user.id))
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise AuthenticationError("Invalid token type.")
            user_id = payload["sub"]
        except JWTError:
            raise AuthenticationError("Invalid or expired refresh token.")

        user_id_val = UUID(user_id) if isinstance(user_id, str) else user_id
        result = await self.db.execute(select(User).where(User.id == user_id_val))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive.")

        from app.core.config import settings
        return TokenResponse(
            access_token=create_access_token(user.id, user.email),
            refresh_token=create_refresh_token(user.id),
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def get_current_user(self, token: str) -> User:
        try:
            payload = decode_token(token)
            if payload.get("type") != "access":
                raise AuthenticationError("Invalid token type.")
            user_id = payload["sub"]
        except JWTError:
            raise AuthenticationError("Invalid or expired access token.")

        user_id_val = UUID(user_id) if isinstance(user_id, str) else user_id
        result = await self.db.execute(select(User).where(User.id == user_id_val))
        user = result.scalar_one_or_none()
        if not user:
            raise AuthenticationError("User not found.")
        if not user.is_active:
            raise AuthenticationError("Account is deactivated.")
        return user


# ── FastAPI Dependency ────────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency that returns the authenticated user or raises 401."""
    if not credentials:
        raise AuthenticationError("Authorization header missing.")
    service = AuthService(db)
    return await service.get_current_user(credentials.credentials)
