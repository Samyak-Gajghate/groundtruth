from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from saas.core.config import settings
from saas.db import set_tenant_guc
from saas.models import Plan, Subscription, SubscriptionStatus, Tenant

if TYPE_CHECKING:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class PlanLimits:
    docs: int
    messages_per_month: int
    cost_budget_usd: float


PLAN_LIMITS: dict[Plan, PlanLimits] = {
    Plan.free: PlanLimits(
        docs=settings.plan_free_docs,
        messages_per_month=settings.plan_free_messages,
        cost_budget_usd=settings.plan_free_cost_budget,
    ),
    Plan.pro: PlanLimits(
        docs=settings.plan_pro_docs,
        messages_per_month=settings.plan_pro_messages,
        cost_budget_usd=settings.plan_pro_cost_budget,
    ),
    Plan.enterprise: PlanLimits(
        docs=settings.plan_enterprise_docs,
        messages_per_month=settings.plan_enterprise_messages,
        cost_budget_usd=settings.plan_enterprise_cost_budget,
    ),
}


async def update_tenant_subscription(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    plan: Plan,
    status: SubscriptionStatus,
    external_id: str | None = None,
) -> Subscription:
    from sqlalchemy import select

    await set_tenant_guc(session, str(tenant_id))
    sub = (
        await session.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
    ).scalar_one()
    tenant = (
        await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    ).scalar_one()

    sub.plan = plan
    sub.status = status
    if external_id is not None:
        sub.external_id = external_id
    tenant.plan = plan
    return sub


@dataclass(frozen=True)
class CheckoutSession:
    url: str
    session_id: str


class BillingProvider(Protocol):
    name: str
    supports_checkout: bool

    async def create_checkout(self, tenant_id: UUID, plan: Plan, return_url: str) -> CheckoutSession:
        """Create a hosted-checkout session for upgrading to `plan`."""
        ...

    async def cancel(self, tenant_id: UUID) -> None: ...

    async def handle_webhook(self, payload: bytes, signature: str | None) -> dict:
        """Verify the webhook signature and apply the resulting state change. Returns
        a small dict describing what happened, suitable for the audit log."""
        ...


def build_billing_provider() -> BillingProvider:
    from saas.billing.mock import MockBillingProvider
    from saas.billing.stripe_provider import StripeBillingProvider

    if settings.billing_provider == "stripe" and settings.stripe_secret_key:
        return StripeBillingProvider()
    return MockBillingProvider()

