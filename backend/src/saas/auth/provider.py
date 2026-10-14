from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class AuthPrincipal:
    user_id: UUID
    tenant_id: UUID
    email: str
    is_admin: bool


class AuthProvider(Protocol):
    name: str
    supports_signup: bool

    async def verify_token(self, token: str) -> AuthPrincipal | None: ...

    async def signup(
        self, email: str, password: str, tenant_name: str
    ) -> tuple[AuthPrincipal, str]:
        """Returns (principal, fresh access token). Raises ValueError on conflict."""
        ...

    async def login(self, email: str, password: str) -> tuple[AuthPrincipal, str]:
        """Returns (principal, fresh access token). Raises ValueError on bad credentials."""
        ...


def build_auth_provider() -> AuthProvider:
    from saas.auth.clerk import ClerkAuthProvider
    from saas.auth.dev import DevAuthProvider
    from saas.core.config import settings

    if settings.auth_provider == "clerk":
        return ClerkAuthProvider()
    return DevAuthProvider()
