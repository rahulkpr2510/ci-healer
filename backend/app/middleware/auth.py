# backend/app/middleware/auth.py

from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.user import User
from app.services.jwt_service import decode_access_token

# Reads the Bearer token from the Authorization header
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Core auth dependency. Use in any protected route:
        current_user: User = Depends(get_current_user)

    Flow:
      1. Extract Bearer token from Authorization header
      2. Decode + validate JWT
      3. Look up user in DB by ID from token
      4. Return User ORM object
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode JWT — raises 401 if invalid/expired
    payload = decode_access_token(credentials.credentials)

    user_id = int(payload["sub"])

    # Fetch user from DB
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Token may be stale.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    return user


async def get_current_user_from_token_or_query(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    token: str | None = Query(default=None, description="JWT token (fallback for SSE)"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Auth dependency that accepts token from either:
    1. Authorization header (Bearer token) - preferred
    2. Query parameter (?token=xxx) - fallback for SSE/EventSource

    Use for SSE endpoints where browsers cannot send custom headers:
        current_user: User = Depends(get_current_user_from_token_or_query)
    """
    # Prefer header-based auth
    jwt_token: str | None = None
    if credentials is not None:
        jwt_token = credentials.credentials
    elif token is not None:
        jwt_token = token

    if jwt_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication provided. Use Authorization header or ?token= query param.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode JWT — raises 401 if invalid/expired
    payload = decode_access_token(jwt_token)
    user_id = int(payload["sub"])

    # Fetch user from DB
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Token may be stale.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Same as get_current_user but returns None instead of 401.
    Use for routes that work both authenticated and unauthenticated.
    """
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials=credentials, db=db)
    except HTTPException:
        return None
