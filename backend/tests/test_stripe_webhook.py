from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from saas.billing.provider import update_tenant_subscription
from saas.billing.stripe_provider import StripeBillingProvider
from saas.core.config import settings
from saas.db import Base
from saas.models import Plan, Subscription, SubscriptionStatus, Tenant

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def async_sqlite_session() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn, tables=[Tenant.__table__, Subscription.__table__]
            )
        )

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    yield session_factory
    await engine.dispose()


@pytest_asyncio.fixture
async def setup_stripe_provider(
    async_sqlite_session: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[StripeBillingProvider, Tenant, Subscription]:
    # Mock settings secrets so webhook check passes
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test")
    monkeypatch.setattr(settings, "stripe_price_pro", "price_pro_123")
    monkeypatch.setattr(settings, "stripe_price_enterprise", "price_ent_456")

    # Mock SessionLocal and GUC setters for SQLite across saas.db, provider, and stripe_provider
    monkeypatch.setattr("saas.db.SessionLocal", async_sqlite_session)
    monkeypatch.setattr("saas.billing.stripe_provider.SessionLocal", async_sqlite_session)

    async def _async_noop(*args, **kwargs) -> None:
        pass

    monkeypatch.setattr("saas.db.set_tenant_guc", _async_noop)
    monkeypatch.setattr("saas.db.set_admin_guc", _async_noop)
    monkeypatch.setattr("saas.billing.provider.set_tenant_guc", _async_noop)
    monkeypatch.setattr("saas.billing.stripe_provider.set_tenant_guc", _async_noop)
    monkeypatch.setattr("saas.billing.stripe_provider.set_admin_guc", _async_noop)

    # Mock stripe.Webhook.construct_event to parse JSON payload
    monkeypatch.setattr(
        "stripe.Webhook.construct_event",
        lambda payload, sig, sec: json.loads(payload.decode("utf-8")),
    )

    tenant_id = uuid.uuid4()
    sub_id = uuid.uuid4()

    async with async_sqlite_session() as s:
        tenant = Tenant(id=tenant_id, name="Test Tenant", slug="test-tenant", plan=Plan.free)
        sub = Subscription(
            id=sub_id,
            tenant_id=tenant_id,
            plan=Plan.free,
            status=SubscriptionStatus.active,
            external_id="sub_stripe_123",
        )
        s.add_all([tenant, sub])
        await s.commit()

    provider = StripeBillingProvider()
    return provider, tenant, sub


async def test_checkout_session_completed_syncs_tenant_and_subscription(
    setup_stripe_provider: tuple[StripeBillingProvider, Tenant, Subscription],
    async_sqlite_session: async_sessionmaker[AsyncSession],
) -> None:
    provider, tenant, _ = setup_stripe_provider
    payload = {
        "id": "evt_checkout_1",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "subscription": "sub_stripe_123",
                "metadata": {"tenant_id": str(tenant.id), "plan": "pro"},
            }
        },
    }

    res = await provider.handle_webhook(json.dumps(payload).encode("utf-8"), signature="sig_test")
    assert res["received"] is True
    assert res["plan"] == "pro"

    async with async_sqlite_session() as s:
        db_tenant = await s.get(Tenant, tenant.id)
        db_sub = (
            await s.execute(
                Subscription.__table__.select().where(Subscription.tenant_id == tenant.id)
            )
        ).first()

        assert db_sub is not None
        assert db_tenant is not None
        assert db_sub.plan == Plan.pro
        assert db_sub.status == SubscriptionStatus.active
        assert db_tenant.plan == Plan.pro


async def test_subscription_updated_plan_upgrade(
    setup_stripe_provider: tuple[StripeBillingProvider, Tenant, Subscription],
    async_sqlite_session: async_sessionmaker[AsyncSession],
) -> None:
    provider, tenant, _ = setup_stripe_provider
    payload = {
        "id": "evt_sub_up_1",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_stripe_123",
                "status": "active",
                "metadata": {"tenant_id": str(tenant.id), "plan": "enterprise"},
            }
        },
    }

    res = await provider.handle_webhook(json.dumps(payload).encode("utf-8"), signature="sig_test")
    assert res["received"] is True
    assert res["plan"] == "enterprise"

    async with async_sqlite_session() as s:
        db_tenant = await s.get(Tenant, tenant.id)
        db_sub = (
            await s.execute(
                Subscription.__table__.select().where(Subscription.tenant_id == tenant.id)
            )
        ).first()

        assert db_sub is not None
        assert db_tenant is not None
        assert db_sub.plan == Plan.enterprise
        assert db_sub.status == SubscriptionStatus.active
        assert db_tenant.plan == Plan.enterprise


async def test_subscription_updated_plan_downgrade_via_price_item(
    setup_stripe_provider: tuple[StripeBillingProvider, Tenant, Subscription],
    async_sqlite_session: async_sessionmaker[AsyncSession],
) -> None:
    provider, tenant, _ = setup_stripe_provider

    # First upgrade to Enterprise
    async with async_sqlite_session() as s:
        await update_tenant_subscription(
            s, tenant.id, plan=Plan.enterprise, status=SubscriptionStatus.active
        )
        await s.commit()

    # Webhook downgrade event with price item for Pro
    payload = {
        "id": "evt_sub_down_1",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_stripe_123",
                "status": "active",
                "metadata": {"tenant_id": str(tenant.id)},
                "items": {"data": [{"price": {"id": "price_pro_123"}}]},
            }
        },
    }

    res = await provider.handle_webhook(json.dumps(payload).encode("utf-8"), signature="sig_test")
    assert res["received"] is True
    assert res["plan"] == "pro"

    async with async_sqlite_session() as s:
        db_tenant = await s.get(Tenant, tenant.id)
        db_sub = (
            await s.execute(
                Subscription.__table__.select().where(Subscription.tenant_id == tenant.id)
            )
        ).first()

        assert db_sub is not None
        assert db_tenant is not None
        assert db_sub.plan == Plan.pro
        assert db_sub.status == SubscriptionStatus.active
        assert db_tenant.plan == Plan.pro


async def test_subscription_updated_past_due_status(
    setup_stripe_provider: tuple[StripeBillingProvider, Tenant, Subscription],
    async_sqlite_session: async_sessionmaker[AsyncSession],
) -> None:
    provider, tenant, _ = setup_stripe_provider

    # Set initial state to Pro / Active
    async with async_sqlite_session() as s:
        await update_tenant_subscription(
            s, tenant.id, plan=Plan.pro, status=SubscriptionStatus.active
        )
        await s.commit()

    payload = {
        "id": "evt_past_due_1",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_stripe_123",
                "status": "past_due",
                "metadata": {"tenant_id": str(tenant.id), "plan": "pro"},
            }
        },
    }

    res = await provider.handle_webhook(json.dumps(payload).encode("utf-8"), signature="sig_test")
    assert res["received"] is True
    assert res["status"] == "past_due"

    async with async_sqlite_session() as s:
        db_tenant = await s.get(Tenant, tenant.id)
        db_sub = (
            await s.execute(
                Subscription.__table__.select().where(Subscription.tenant_id == tenant.id)
            )
        ).first()

        assert db_sub is not None
        assert db_tenant is not None
        assert db_sub.plan == Plan.pro
        assert db_sub.status == SubscriptionStatus.past_due
        assert db_tenant.plan == Plan.pro


async def test_subscription_deleted_cancellation(
    setup_stripe_provider: tuple[StripeBillingProvider, Tenant, Subscription],
    async_sqlite_session: async_sessionmaker[AsyncSession],
) -> None:
    provider, tenant, _ = setup_stripe_provider

    # Set initial state to Pro / Active
    async with async_sqlite_session() as s:
        await update_tenant_subscription(
            s, tenant.id, plan=Plan.pro, status=SubscriptionStatus.active
        )
        await s.commit()

    payload = {
        "id": "evt_deleted_1",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_stripe_123",
                "status": "canceled",
                "metadata": {"tenant_id": str(tenant.id)},
            }
        },
    }

    res = await provider.handle_webhook(json.dumps(payload).encode("utf-8"), signature="sig_test")
    assert res["received"] is True
    assert res["status"] == "canceled"

    async with async_sqlite_session() as s:
        db_tenant = await s.get(Tenant, tenant.id)
        db_sub = (
            await s.execute(
                Subscription.__table__.select().where(Subscription.tenant_id == tenant.id)
            )
        ).first()

        assert db_sub is not None
        assert db_tenant is not None
        assert db_sub.plan == Plan.free
        assert db_sub.status == SubscriptionStatus.canceled
        assert db_tenant.plan == Plan.free
