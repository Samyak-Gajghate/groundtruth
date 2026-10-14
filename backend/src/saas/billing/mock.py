from __future__ import annotations

import secrets
from uuid import UUID

from sqlalchemy import select

from saas.billing.provider import CheckoutSession, update_tenant_subscription
from saas.core.logging import get_logger
from saas.db import SessionLocal
from saas.models import Plan, SubscriptionStatus

log = get_logger(__name__)


class MockBillingProvider:
    """Stand-in for Stripe during dev/demo.

    `create_checkout` returns a synthetic URL that the frontend treats like Stripe's
    hosted checkout — clicking 'Pay' on the mock page POSTs to a confirm endpoint
    that calls back into `confirm_session` here. No real card flow, but the
    state machine (active/canceled/past_due) is exercised end-to-end.
    """

    name = "mock"
    supports_checkout = True
    _sessions: dict[str, tuple[UUID, Plan]] = {}

    async def create_checkout(self, tenant_id: UUID, plan: Plan, return_url: str) -> CheckoutSession:
        sid = "mock_cs_" + secrets.token_urlsafe(16)
        self._sessions[sid] = (tenant_id, plan)
        url = f"/billing/mock-checkout?session_id={sid}&return_url={return_url}"
        log.info("mock_checkout_created", tenant_id=str(tenant_id), plan=plan.value, sid=sid)
        return CheckoutSession(url=url, session_id=sid)

    async def confirm_session(self, session_id: str) -> tuple[UUID, Plan]:
        """Mock-only: the mock checkout page calls this to apply the upgrade."""
        entry = self._sessions.pop(session_id, None)
        if entry is None:
            raise ValueError("unknown checkout session")
        tenant_id, plan = entry
        async with SessionLocal() as session:
            await update_tenant_subscription(
                session,
                tenant_id,
                plan=plan,
                status=SubscriptionStatus.active,
                external_id=session_id,
            )
            await session.commit()
        log.info("mock_checkout_confirmed", tenant_id=str(tenant_id), plan=plan.value)
        return tenant_id, plan

    async def cancel(self, tenant_id: UUID) -> None:
        async with SessionLocal() as session:
            await update_tenant_subscription(
                session,
                tenant_id,
                plan=Plan.free,
                status=SubscriptionStatus.canceled,
            )
            await session.commit()
        log.info("mock_subscription_canceled", tenant_id=str(tenant_id))

    async def handle_webhook(self, payload: bytes, signature: str | None) -> dict:
        # Mock provider doesn't receive webhooks; this endpoint is a no-op so the
        # route remains routable when BILLING_PROVIDER=mock.
        return {"received": False, "provider": "mock"}
