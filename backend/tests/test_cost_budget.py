from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from saas.billing.provider import PLAN_LIMITS
from saas.chat.stream import PlanLimitExceeded, stream_chat
from saas.db import Base
from saas.models import (
    Conversation,
    ConversationChannel,
    Message,
    Plan,
    Subscription,
    SubscriptionStatus,
    Tenant,
    UsageEvent,
)

pytestmark = pytest.mark.asyncio


from sqlalchemy import event


@pytest_asyncio.fixture
async def async_sqlite_session() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def _register_sqlite_funcs(dbapi_connection, connection_record) -> None:
        dbapi_connection.create_function(
            "date_trunc", 2, lambda fmt, ts: (str(ts)[:7] + "-01 00:00:00") if ts else None
        )

    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    Tenant.__table__,
                    Subscription.__table__,
                    UsageEvent.__table__,
                ],
            )
        )

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    yield session_factory
    await engine.dispose()


async def test_chat_proceeds_when_under_cost_budget(
    async_sqlite_session: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    async with async_sqlite_session() as s:
        tenant = Tenant(id=tenant_id, name="Under Budget Tenant", slug="under-budget", plan=Plan.free)
        sub = Subscription(tenant_id=tenant_id, plan=Plan.free, status=SubscriptionStatus.active)
        # Small usage event well under $5.00 budget
        usage = UsageEvent(tenant_id=tenant_id, kind="chat", model="claude", cost_usd=0.50)
        s.add_all([tenant, sub, usage])
        await s.commit()

    monkeypatch.setattr("saas.chat.stream._check_message_quota", AsyncMock())
    monkeypatch.setattr("saas.chat.stream.retrieve_for_tenant", AsyncMock(return_value=[]))

    async def _mock_claude_stream(*args, **kwargs) -> AsyncIterator[tuple[str, int, int]]:
        yield "Hello", 10, 10

    monkeypatch.setattr("saas.chat.stream.claude_stream", _mock_claude_stream)
    monkeypatch.setattr(
        "saas.chat.stream._get_or_create_conversation",
        AsyncMock(return_value=AsyncMock(id=uuid.uuid4())),
    )

    async with async_sqlite_session() as s:
        monkeypatch.setattr(s, "add", lambda x: None)
        monkeypatch.setattr(s, "commit", AsyncMock())
        events = []
        async for ev in stream_chat(
            s, tenant_id, "Hello", end_user_session="test", channel=ConversationChannel.dashboard
        ):
            events.append(ev)
        assert len(events) > 0


async def test_chat_blocked_and_claude_prevented_when_over_cost_budget(
    async_sqlite_session: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid.uuid4()
    free_budget = PLAN_LIMITS[Plan.free].cost_budget_usd

    async with async_sqlite_session() as s:
        tenant = Tenant(id=tenant_id, name="Over Budget Tenant", slug="over-budget", plan=Plan.free)
        sub = Subscription(tenant_id=tenant_id, plan=Plan.free, status=SubscriptionStatus.active)
        # Seed usage event that equals or exceeds the free plan budget
        usage = UsageEvent(
            tenant_id=tenant_id,
            kind="chat",
            model="claude",
            cost_usd=free_budget + 0.10,
        )
        s.add_all([tenant, sub, usage])
        await s.commit()

    mock_claude = AsyncMock()
    monkeypatch.setattr("saas.chat.stream._check_message_quota", AsyncMock())
    monkeypatch.setattr("saas.chat.stream.claude_stream", mock_claude)
    monkeypatch.setattr("saas.chat.stream.retrieve_for_tenant", AsyncMock(return_value=[]))

    async with async_sqlite_session() as s:
        with pytest.raises(PlanLimitExceeded) as exc_info:
            async for _ in stream_chat(
                s, tenant_id, "High cost test query", end_user_session="test", channel=ConversationChannel.dashboard
            ):
                pass

        assert "cost budget reached for plan free" in str(exc_info.value)

    # CRITICAL ASSERTION: Prove that claude_stream was NEVER invoked when budget check failed
    mock_claude.assert_not_called()
    assert mock_claude.call_count == 0
