import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from db import get_db
from models import APIKey, RefreshTokenJti, User

JWT_SECRET = os.environ.get("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")
AUTH_DISABLED = os.environ.get("AUTH_DISABLED", "").lower() in {"1", "true", "yes", "on"}

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def dummy_verify_password() -> None:
    """Burn the same bcrypt cycles as a real verify so login timing doesn't leak whether an email exists."""
    pwd_context.dummy_verify()


def generate_api_key() -> tuple[str, str, str]:
    """Returns (full_key, prefix, hash)."""
    raw = secrets.token_urlsafe(32)
    full_key = f"m0sk_{raw}"
    prefix = full_key[:12]
    key_hash = pwd_context.hash(full_key)
    return full_key, prefix, key_hash


def verify_api_key_hash(plain_key: str, hashed: str) -> bool:
    return pwd_context.verify(plain_key, hashed)


def _get_secret() -> str:
    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT_SECRET is not configured.")
    return JWT_SECRET


def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "role": role, "exp": expire, "type": "access"}
    return jwt.encode(payload, _get_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str, db: Session) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    jti = uuid.uuid4()
    db.add(RefreshTokenJti(jti=jti, user_id=uuid.UUID(user_id), expires_at=expire))
    db.commit()
    payload = {"sub": user_id, "exp": expire, "jti": str(jti), "type": "refresh"}
    return jwt.encode(payload, _get_secret(), algorithm=JWT_ALGORITHM)


def consume_refresh_jti(jti: str, db: Session) -> None:
    """Atomically mark a refresh token's jti as used. Raises 401 if missing, already used, or expired.

    The conditional UPDATE closes the read-check-write race: concurrent replays of the same
    token race on a single row, so at most one update affects a row and the rest see rowcount 0.
    """
    try:
        jti_uuid = uuid.UUID(jti)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Refresh token is no longer valid.")
    now = datetime.now(timezone.utc)
    result = db.execute(
        update(RefreshTokenJti)
        .where(
            RefreshTokenJti.jti == jti_uuid,
            RefreshTokenJti.used_at.is_(None),
            RefreshTokenJti.expires_at > now,
        )
        .values(used_at=now)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=401, detail="Refresh token is no longer valid.")
    db.commit()


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, _get_secret(), algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")


bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _mark_auth_type(request: Request, auth_type: str) -> None:
    request.state.auth_type = auth_type


def _get_default_user(db: Session) -> User | None:
    return db.scalar(select(User).order_by(User.created_at.asc()))


def _resolve_user_from_jwt(token: str, db: Session) -> User:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type.")
    user = db.get(User, payload.get("sub"))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


def _resolve_user_from_api_key(key: str, db: Session) -> User:
    prefix = key[:12] if len(key) >= 12 else key
    candidates = (
        db.execute(select(APIKey).where(APIKey.key_prefix == prefix, APIKey.revoked_at.is_(None))).scalars().all()
    )

    for candidate in candidates:
        if verify_api_key_hash(key, candidate.key_hash):
            candidate.last_used_at = datetime.now(timezone.utc)
            db.commit()
            user = db.get(User, candidate.created_by)
            if user is None:
                raise HTTPException(status_code=401, detail="API key owner not found.")
            return user

    raise HTTPException(status_code=401, detail="Invalid API key.")


def _resolve_via_api_key(request: Request, key: str, db: Session) -> User | None:
    """Resolve ``key`` against ADMIN_API_KEY first, then the per-user APIKey table.

    Marks ``request.state.auth_type`` (``admin_api_key`` for the legacy admin
    shortcut, ``api_key`` for a per-user key) and returns the User — ``None``
    for the admin path, matching the contract ``require_auth`` already relies
    on for the default-user fallback in single-tenant deployments.
    """
    if ADMIN_API_KEY and secrets.compare_digest(key, ADMIN_API_KEY):
        _mark_auth_type(request, "admin_api_key")
        return None
    _mark_auth_type(request, "api_key")
    return _resolve_user_from_api_key(key, db)


async def verify_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_api_key: str | None = Depends(api_key_header),
    db: Session = Depends(get_db),
) -> User | None:
    """Authenticate a request and resolve the calling User.

    Resolution order:
      1. ``Authorization: Token <key>``  → API-key path. Matches the mem0
         hosted-platform convention (and what the OpenClaw plugin sends).
         ``HTTPBearer`` only parses the ``Bearer`` scheme per RFC 6750, so
         we read the ``Authorization`` header directly to catch ``Token``.
      2. ``Authorization: Bearer <val>`` → try JWT decode first; on
         ``JWTError`` fall back to the API-key path. Lets clients that
         accidentally send their API key in the Bearer slot still work
         (a common mistake from SDKs that assume Bearer is universal).
      3. ``X-API-Key: <key>``            → API-key path. Unchanged.
      4. ``AUTH_DISABLED=true``          → no-op pass-through (dev only).

    Returns the resolved ``User`` or ``None`` for admin/disabled paths;
    ``require_auth`` translates ``None`` into the default user for legacy
    single-tenant deployments.
    """
    # Authorization: Token <key>  — HTTPBearer ignores non-Bearer schemes
    # (auto_error=False, returns None), so parse the header ourselves.
    auth_header = request.headers.get("Authorization", "")
    if auth_header:
        scheme, _, value = auth_header.partition(" ")
        if scheme.lower() == "token" and value:
            return _resolve_via_api_key(request, value, db)

    # Authorization: Bearer <val>  — JWT first, fall back to API key on JWTError.
    if credentials is not None:
        token = credentials.credentials
        try:
            payload = jwt.decode(token, _get_secret(), algorithms=[JWT_ALGORITHM])
        except JWTError:
            # Not a JWT — treat the Bearer payload as an API key.
            return _resolve_via_api_key(request, token, db)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type.")
        sub = payload.get("sub")
        # ``users.id`` is a UUID column. PostgreSQL accepts string PKs in
        # ``Session.get``; SQLite (used by tests) does not, so coerce here.
        try:
            user_pk = uuid.UUID(sub) if isinstance(sub, str) else sub
        except (TypeError, ValueError):
            raise HTTPException(status_code=401, detail="User not found.")
        user = db.get(User, user_pk)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found.")
        _mark_auth_type(request, "bearer")
        return user

    if x_api_key is not None:
        return _resolve_via_api_key(request, x_api_key, db)

    if AUTH_DISABLED:
        _mark_auth_type(request, "disabled")
        return None

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide a Bearer token or X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_auth(
    request: Request,
    user: User | None = Depends(verify_auth),
    db: Session = Depends(get_db),
) -> User:
    """Like verify_auth but guarantees a non-None User. Use for endpoints that require auth."""
    if user is None:
        if getattr(request.state, "auth_type", "none") in {"admin_api_key", "disabled"}:
            default_user = _get_default_user(db)
            if default_user is not None:
                return default_user
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user
