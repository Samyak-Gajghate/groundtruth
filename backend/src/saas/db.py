from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from saas.core.config import settings

# Sentinel value that the RLS policy recognizes as a bootstrap bypass.
# Only the signup path (and equivalent system-level operations) should set this.
# Any path that forgets to call set_tenant_guc/set_admin_guc gets an EMPTY GUC,
# which the policy treats as "no tenant scope" → zero rows visible. Fail-closed.
ADMIN_BYPASS_TOKEN = "__bootstrap__"


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=10,
    future=True,
)

SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as s:
        try:
            yield s
        except Exception:
            await s.rollback()
            raise


async def set_tenant_guc(session: AsyncSession, tenant_id: str | None) -> None:
    """Set `app.tenant_id` as a session GUC for RLS scoping.

    - `tenant_id="<uuid>"` → policy matches rows where tenant_id::text equals it.
    - `tenant_id=None`     → GUC is empty; policy matches zero rows (fail-closed).

    Use `set_config(..., is_local=true)` so the value only persists for the
    current transaction. Safe to call repeatedly within a request.
    """
    value = tenant_id if tenant_id is not None else ""
    await session.execute(
        text("SELECT set_config('app.tenant_id', :t, true)"),
        {"t": value},
    )


async def set_admin_guc(session: AsyncSession) -> None:
    """Engage the bootstrap bypass for legitimate cross-tenant admin operations
    (signup, internal maintenance). The RLS policy treats `ADMIN_BYPASS_TOKEN`
    as an explicit signal that *this code path knows it needs cross-tenant
    access*. Use sparingly: any handler that calls this must enforce its own
    authorization. Default (no GUC set) is fail-closed."""
    await session.execute(
        text("SELECT set_config('app.tenant_id', :t, true)"),
        {"t": ADMIN_BYPASS_TOKEN},
    )
