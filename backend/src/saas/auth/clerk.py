from __future__ import annotations

from uuid import UUID

import httpx
from sqlalchemy import select

from saas.auth.provider import AuthPrincipal
from saas.core.config import settings
from saas.core.logging import get_logger
from saas.db import SessionLocal, set_admin_guc
from saas.models import Tenant, User

log = get_logger(__name__)


class ClerkAuthProvider:
    """Clerk session-token verifier. Calls Clerk's /v1/sessions/verify endpoint;
    on success, finds or creates a local User+Tenant mapped to the Clerk user.

    Activate by setting AUTH_PROVIDER=clerk and CLERK_SECRET_KEY. The dev
    provider is the default so this entire module is dormant unless wired up.
    """

    name = "clerk"
    supports_signup = False  # Clerk handles signup in its own SDK on the frontend.

    async def verify_token(self, token: str) -> AuthPrincipal | None:
        if not settings.clerk_secret_key:
            log.warning("clerk_secret_key_missing")
            return None
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://api.clerk.com/v1/me",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code != 200:
                    return None
                me = resp.json()
        except httpx.HTTPError as exc:
            log.warning("clerk_verify_failed", error=str(exc))
            return None

        external_id: str = me.get("id", "")
        email = next((e.get("email_address") for e in me.get("email_addresses", []) if e), None)
        org_id: str | None = me.get("organization_id")
        if not external_id or not email or not org_id:
            return None

        async with SessionLocal() as session:
            # Clerk-token verification creates a local tenant+user the first time we
            # see them. Same cross-tenant bootstrap pattern as the dev signup.
            await set_admin_guc(session)
            tenant = (
                await session.execute(select(Tenant).where(Tenant.slug == org_id))
            ).scalar_one_or_none()
            if tenant is None:
                tenant = Tenant(name=org_id, slug=org_id)
                session.add(tenant)
                await session.flush()
            user = (
                await session.execute(
                    select(User).where(User.tenant_id == tenant.id, User.email == email)
                )
            ).scalar_one_or_none()
            if user is None:
                user = User(
                    tenant_id=tenant.id, email=email, external_id=external_id, is_admin=True
                )
                session.add(user)
                await session.commit()
            return AuthPrincipal(
                user_id=user.id,
                tenant_id=tenant.id,
                email=email,
                is_admin=user.is_admin,
            )

    async def signup(self, *_args, **_kwargs) -> tuple[AuthPrincipal, str]:  # type: ignore[no-untyped-def]
        raise NotImplementedError("Clerk handles signup; use the Clerk SDK on the frontend")

    async def login(self, *_args, **_kwargs) -> tuple[AuthPrincipal, str]:  # type: ignore[no-untyped-def]
        raise NotImplementedError("Clerk handles login; use the Clerk SDK on the frontend")
