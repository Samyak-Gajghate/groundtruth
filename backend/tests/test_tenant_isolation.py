"""Integration test for the RLS isolation model.

Boots two tenants, gives each a document, and asserts the four GUC states
behave exactly as documented in docs/multi-tenancy.md:

  1. Tenant A's session sees only A's row.
  2. Tenant B's session sees only B's row.
  3. Unscoped session (GUC unset) sees zero rows — fail-closed.
  4. Bootstrap-scoped session sees both rows — bypass works.

Requires a running Postgres at $DATABASE_URL with migrations applied.
Auto-skipped when the DB is not reachable so `pytest` still passes in
environments without infrastructure.

Run with:
    docker compose exec backend pytest -v tests/test_tenant_isolation.py
"""
from __future__ import annotations

import secrets
import uuid
from typing import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import delete, select, text

from saas.db import (
    ADMIN_BYPASS_TOKEN,
    SessionLocal,
    engine,
    set_admin_guc,
    set_tenant_guc,
)
from saas.models import (
    Chunk,
    Document,
    Subscription,
    Tenant,
    User,
)

pytestmark = pytest.mark.asyncio


async def _db_reachable() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest_asyncio.fixture
async def two_tenants() -> AsyncIterator[tuple[Tenant, Document, Tenant, Document]]:
    """Create two tenants each with one document, then yield them and clean up."""
    if not await _db_reachable():
        pytest.skip("DATABASE_URL not reachable; skipping integration test")

    suffix = secrets.token_hex(4)
    tenant_a_id = uuid.uuid4()
    tenant_b_id = uuid.uuid4()
    doc_a_id = uuid.uuid4()
    doc_b_id = uuid.uuid4()

    async with SessionLocal() as s:
        await set_admin_guc(s)  # bootstrap insert
        s.add_all(
            [
                Tenant(id=tenant_a_id, name=f"Tenant A {suffix}", slug=f"tenant-a-{suffix}"),
                Tenant(id=tenant_b_id, name=f"Tenant B {suffix}", slug=f"tenant-b-{suffix}"),
            ]
        )
        await s.flush()
        s.add_all(
            [
                Subscription(tenant_id=tenant_a_id),
                Subscription(tenant_id=tenant_b_id),
                Document(
                    id=doc_a_id,
                    tenant_id=tenant_a_id,
                    filename="a.pdf",
                    content_hash=f"a-{suffix}",
                    byte_size=1,
                ),
                Document(
                    id=doc_b_id,
                    tenant_id=tenant_b_id,
                    filename="b.pdf",
                    content_hash=f"b-{suffix}",
                    byte_size=1,
                ),
            ]
        )
        await s.commit()
        tenant_a = await s.get(Tenant, tenant_a_id)
        tenant_b = await s.get(Tenant, tenant_b_id)
        doc_a = await s.get(Document, doc_a_id)
        doc_b = await s.get(Document, doc_b_id)

    try:
        yield tenant_a, doc_a, tenant_b, doc_b  # type: ignore[misc]
    finally:
        async with SessionLocal() as s:
            await set_admin_guc(s)
            await s.execute(delete(Chunk).where(Chunk.tenant_id.in_([tenant_a_id, tenant_b_id])))
            await s.execute(delete(Subscription).where(Subscription.tenant_id.in_([tenant_a_id, tenant_b_id])))
            await s.execute(delete(User).where(User.tenant_id.in_([tenant_a_id, tenant_b_id])))
            await s.execute(delete(Document).where(Document.tenant_id.in_([tenant_a_id, tenant_b_id])))
            await s.execute(delete(Tenant).where(Tenant.id.in_([tenant_a_id, tenant_b_id])))
            await s.commit()


async def _doc_ids_visible(tenant_filter=None) -> set[uuid.UUID]:
    async with SessionLocal() as s:
        if tenant_filter == "A":
            await set_tenant_guc(s, str(_pytest_state["a_id"]))
        elif tenant_filter == "B":
            await set_tenant_guc(s, str(_pytest_state["b_id"]))
        elif tenant_filter == "unset":
            await set_tenant_guc(s, None)
        elif tenant_filter == "admin":
            await set_admin_guc(s)
        rows = (await s.execute(select(Document.id))).scalars().all()
        return set(rows)


_pytest_state: dict[str, uuid.UUID] = {}


async def test_tenant_a_sees_only_a(two_tenants: tuple[Tenant, Document, Tenant, Document]) -> None:
    a, doc_a, b, doc_b = two_tenants
    _pytest_state["a_id"], _pytest_state["b_id"] = a.id, b.id
    visible = await _doc_ids_visible("A")
    assert doc_a.id in visible
    assert doc_b.id not in visible


async def test_tenant_b_sees_only_b(two_tenants: tuple[Tenant, Document, Tenant, Document]) -> None:
    a, doc_a, b, doc_b = two_tenants
    _pytest_state["a_id"], _pytest_state["b_id"] = a.id, b.id
    visible = await _doc_ids_visible("B")
    assert doc_b.id in visible
    assert doc_a.id not in visible


async def test_unscoped_session_sees_zero_docs(
    two_tenants: tuple[Tenant, Document, Tenant, Document],
) -> None:
    """The whole point of the security model: forgetting to set the GUC is
    fail-closed, not fail-open. An unscoped session must see zero RLS-protected
    rows, even though two tenants' documents exist."""
    a, doc_a, b, doc_b = two_tenants
    _pytest_state["a_id"], _pytest_state["b_id"] = a.id, b.id
    visible = await _doc_ids_visible("unset")
    assert doc_a.id not in visible
    assert doc_b.id not in visible


async def test_admin_bypass_sees_both(
    two_tenants: tuple[Tenant, Document, Tenant, Document],
) -> None:
    """Explicit bootstrap bypass is the only path that legitimately sees
    cross-tenant rows. Used by signup/login; any other use is a code smell."""
    a, doc_a, b, doc_b = two_tenants
    _pytest_state["a_id"], _pytest_state["b_id"] = a.id, b.id
    visible = await _doc_ids_visible("admin")
    assert doc_a.id in visible
    assert doc_b.id in visible


async def test_cross_tenant_write_check_fails(
    two_tenants: tuple[Tenant, Document, Tenant, Document],
) -> None:
    """WITH CHECK clause must reject INSERTs whose tenant_id doesn't match the
    GUC. This is the write-side guarantee — a tenant A-scoped session cannot
    smuggle a row into tenant B by setting tenant_id directly."""
    a, _doc_a, b, _doc_b = two_tenants
    async with SessionLocal() as s:
        await set_tenant_guc(s, str(a.id))
        # Try to insert a chunk that claims to belong to tenant B while the
        # session is scoped to tenant A.
        s.add(
            Chunk(
                tenant_id=b.id,
                document_id=_doc_b.id,
                chunk_index=0,
                content="cross-tenant smuggling attempt",
                token_count=4,
                embedding=[0.0] * 1536,
            )
        )
        with pytest.raises(Exception):
            await s.commit()
