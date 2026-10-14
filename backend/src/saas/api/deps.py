from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from saas.auth.provider import AuthPrincipal, AuthProvider, build_auth_provider
from saas.billing.provider import BillingProvider, build_billing_provider
from saas.db import SessionLocal, set_tenant_guc
from saas.tenancy.context import set_current_tenant


@lru_cache(maxsize=1)
def _auth() -> AuthProvider:
    return build_auth_provider()


@lru_cache(maxsize=1)
def _billing() -> BillingProvider:
    return build_billing_provider()


def get_auth_provider() -> AuthProvider:
    return _auth()


def get_billing_provider() -> BillingProvider:
    return _billing()


async def get_principal(
    authorization: str | None = Header(default=None),
    auth: AuthProvider = Depends(get_auth_provider),
) -> AuthPrincipal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    principal = await auth.verify_token(token)
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    return principal


async def tenant_scoped_session(
    principal: AuthPrincipal = Depends(get_principal),
) -> AsyncIterator[AsyncSession]:
    """Yield a DB session with `app.tenant_id` set so RLS scopes every query."""
    set_current_tenant(principal.tenant_id)
    async with SessionLocal() as s:
        try:
            await set_tenant_guc(s, str(principal.tenant_id))
            yield s
        except Exception:
            await s.rollback()
            raise
        finally:
            set_current_tenant(None)
