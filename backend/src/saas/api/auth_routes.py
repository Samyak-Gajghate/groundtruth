from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from saas.api.deps import get_auth_provider, get_principal, tenant_scoped_session
from saas.auth.provider import AuthPrincipal, AuthProvider
from saas.core.logging import get_logger
from saas.models import Tenant

router = APIRouter(prefix="/auth", tags=["auth"])
log = get_logger(__name__)


class SignupIn(BaseModel):
    email: str = Field(min_length=4, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    tenant_name: str = Field(min_length=2, max_length=200)


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    tenant_id: str
    email: str
    is_admin: bool


class MeOut(BaseModel):
    user_id: str
    tenant_id: str
    tenant_name: str
    tenant_slug: str
    tenant_public_key: str
    plan: str
    email: str
    is_admin: bool


def _token_out(principal: AuthPrincipal, token: str) -> TokenOut:
    return TokenOut(
        access_token=token,
        user_id=str(principal.user_id),
        tenant_id=str(principal.tenant_id),
        email=principal.email,
        is_admin=principal.is_admin,
    )


@router.post("/signup", response_model=TokenOut)
async def signup(body: SignupIn, auth: AuthProvider = Depends(get_auth_provider)) -> TokenOut:
    if not auth.supports_signup:
        raise HTTPException(
            status_code=400,
            detail=f"signup not supported by {auth.name} provider — use the SDK on the frontend",
        )
    try:
        principal, token = await auth.signup(body.email, body.password, body.tenant_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _token_out(principal, token)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, auth: AuthProvider = Depends(get_auth_provider)) -> TokenOut:
    try:
        principal, token = await auth.login(body.email, body.password)
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid credentials") from None
    return _token_out(principal, token)


@router.get("/me", response_model=MeOut)
async def me(
    principal: AuthPrincipal = Depends(get_principal),
    session: AsyncSession = Depends(tenant_scoped_session),
) -> MeOut:
    tenant = (
        await session.execute(select(Tenant).where(Tenant.id == principal.tenant_id))
    ).scalar_one()
    return MeOut(
        user_id=str(principal.user_id),
        tenant_id=str(principal.tenant_id),
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
        tenant_public_key=tenant.public_key,
        plan=tenant.plan.value,
        email=principal.email,
        is_admin=principal.is_admin,
    )
