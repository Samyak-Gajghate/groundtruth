from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
from passlib.context import CryptContext
from sqlalchemy import select

from saas.auth.provider import AuthPrincipal
from saas.core.config import settings
from saas.core.logging import get_logger
from saas.db import SessionLocal, set_admin_guc, set_tenant_guc
from saas.models import Subscription, Tenant, User

log = get_logger(__name__)

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def _make_slug(name: str) -> str:
    s = _SLUG_RE.sub("-", name.lower()).strip("-")
    return s[:48] or f"tenant-{uuid4().hex[:8]}"


def _encode(principal: AuthPrincipal) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(principal.user_id),
        "tenant": str(principal.tenant_id),
        "email": principal.email,
        "admin": principal.is_admin,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


class DevAuthProvider:
    """Email/password auth, HS256 JWTs, signup creates a Tenant + first User + free Subscription.

    Production replacement: ClerkAuthProvider, which verifies tokens against Clerk's JWKS.
    The dashboard never branches on which provider is active; this class fully implements
    the same Protocol so the swap is one env var."""

    name = "dev"
    supports_signup = True

    async def verify_token(self, token: str) -> AuthPrincipal | None:
        try:
            data = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        except jwt.PyJWTError as exc:
            log.info("jwt_verify_failed", error=str(exc))
            return None
        try:
            return AuthPrincipal(
                user_id=UUID(data["sub"]),
                tenant_id=UUID(data["tenant"]),
                email=str(data["email"]),
                is_admin=bool(data.get("admin", False)),
            )
        except (KeyError, ValueError):
            return None

    async def signup(
        self, email: str, password: str, tenant_name: str
    ) -> tuple[AuthPrincipal, str]:
        if not _EMAIL_RE.match(email):
            raise ValueError("invalid email")
        if len(password) < 8:
            raise ValueError("password must be at least 8 characters")
        if not tenant_name.strip():
            raise ValueError("tenant_name required")

        async with SessionLocal() as session:
            # Signup is the only legitimate cross-tenant write path: we need to
            # detect duplicate emails across all tenants AND insert the first
            # user+subscription row before any tenant scope exists. Engage the
            # explicit bootstrap bypass.
            await set_admin_guc(session)
            existing = await session.execute(select(User).where(User.email == email))
            if existing.scalar_one_or_none() is not None:
                raise ValueError("an account with this email already exists")

            tenant = Tenant(name=tenant_name.strip(), slug=_make_slug(tenant_name))
            session.add(tenant)
            await session.flush()

            session.add(Subscription(tenant_id=tenant.id))

            user = User(
                tenant_id=tenant.id,
                email=email,
                password_hash=_pwd.hash(password),
                is_admin=True,
            )
            session.add(user)
            await session.commit()
            principal = AuthPrincipal(
                user_id=user.id,
                tenant_id=tenant.id,
                email=email,
                is_admin=True,
            )
            return principal, _encode(principal)

    async def login(self, email: str, password: str) -> tuple[AuthPrincipal, str]:
        async with SessionLocal() as session:
            # Login looks up a user by email before any tenant context exists;
            # cross-tenant read is intentional. Bootstrap bypass is the right
            # scope here — the password check below is the actual authorization.
            await set_admin_guc(session)
            user = (
                await session.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if user is None or not user.password_hash:
                raise ValueError("invalid credentials")
            if not _pwd.verify(password, user.password_hash):
                raise ValueError("invalid credentials")
            principal = AuthPrincipal(
                user_id=user.id,
                tenant_id=user.tenant_id,
                email=user.email,
                is_admin=user.is_admin,
            )
            return principal, _encode(principal)
