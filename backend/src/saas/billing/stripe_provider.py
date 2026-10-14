from __future__ import annotations

from uuid import UUID

import stripe
from sqlalchemy import select

from saas.billing.provider import CheckoutSession, update_tenant_subscription
from saas.core.config import settings
from saas.core.logging import get_logger
from saas.db import SessionLocal, set_admin_guc, set_tenant_guc
from saas.models import Plan, Subscription, SubscriptionStatus

log = get_logger(__name__)

def _plan_by_price() -> dict[str, Plan]:
    mapping: dict[str, Plan] = {}
    if settings.stripe_price_pro:
        mapping[settings.stripe_price_pro] = Plan.pro
    if settings.stripe_price_enterprise:
        mapping[settings.stripe_price_enterprise] = Plan.enterprise
    return mapping


_STRIPE_STATUS_MAP: dict[str, SubscriptionStatus] = {
    "active": SubscriptionStatus.active,
    "trialing": SubscriptionStatus.trialing,
    "past_due": SubscriptionStatus.past_due,
    "unpaid": SubscriptionStatus.past_due,
    "canceled": SubscriptionStatus.canceled,
    "incomplete": SubscriptionStatus.past_due,
    "incomplete_expired": SubscriptionStatus.canceled,
    "paused": SubscriptionStatus.past_due,
}


class StripeBillingProvider:
    """Real Stripe Checkout integration. Activated by BILLING_PROVIDER=stripe
    plus a populated STRIPE_SECRET_KEY. The dashboard never branches on which
    provider is active; both share the same surface via `BillingProvider`.
    """

    name = "stripe"
    supports_checkout = True

    def __init__(self) -> None:
        stripe.api_key = settings.stripe_secret_key

    async def create_checkout(self, tenant_id: UUID, plan: Plan, return_url: str) -> CheckoutSession:
        if plan == Plan.free:
            raise ValueError("cannot checkout into the free plan")
        price = _PRICE_BY_PLAN.get(plan)
        if not price:
            raise ValueError(f"STRIPE_PRICE_{plan.value.upper()} env not set")
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price, "quantity": 1}],
            success_url=return_url + "?ok=1",
            cancel_url=return_url + "?ok=0",
            client_reference_id=str(tenant_id),
            metadata={"tenant_id": str(tenant_id), "plan": plan.value},
            subscription_data={"metadata": {"tenant_id": str(tenant_id), "plan": plan.value}},
        )
        log.info("stripe_checkout_created", tenant_id=str(tenant_id), plan=plan.value)
        return CheckoutSession(url=session.url or "", session_id=session.id)

    async def cancel(self, tenant_id: UUID) -> None:
        async with SessionLocal() as session:
            await set_tenant_guc(session, str(tenant_id))
            sub = (
                await session.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
            ).scalar_one()
            if sub.external_id:
                stripe.Subscription.delete(sub.external_id)
            await update_tenant_subscription(
                session, tenant_id, plan=Plan.free, status=SubscriptionStatus.canceled
            )
            await session.commit()
        log.info("stripe_subscription_canceled", tenant_id=str(tenant_id))

    async def handle_webhook(self, payload: bytes, signature: str | None) -> dict:
        if not settings.stripe_webhook_secret or not signature:
            return {"received": False, "reason": "missing signature secret"}
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.stripe_webhook_secret
            )
        except (stripe.error.SignatureVerificationError, ValueError) as exc:
            log.warning("stripe_webhook_bad_signature", error=str(exc))
            return {"received": False, "reason": "bad signature"}

        et = event["type"]
        data = event["data"]["object"]

        if et == "checkout.session.completed":
            tenant_id = UUID(data["metadata"]["tenant_id"])
            plan = Plan(data["metadata"]["plan"])
            external_id = data.get("subscription")
            async with SessionLocal() as session:
                await update_tenant_subscription(
                    session,
                    tenant_id,
                    plan=plan,
                    status=SubscriptionStatus.active,
                    external_id=external_id,
                )
                await session.commit()
            return {"received": True, "type": et, "tenant_id": str(tenant_id), "plan": plan.value}

        if et in ("customer.subscription.deleted", "customer.subscription.updated"):
            tenant_id_meta = data.get("metadata", {}).get("tenant_id")
            sub_id = data.get("id")

            async with SessionLocal() as session:
                sub = None
                if tenant_id_meta:
                    try:
                        tenant_id = UUID(tenant_id_meta)
                        await set_tenant_guc(session, str(tenant_id))
                        sub = (
                            await session.execute(
                                select(Subscription).where(Subscription.tenant_id == tenant_id)
                            )
                        ).scalar_one_or_none()
                    except ValueError:
                        pass

                if sub is None and sub_id:
                    await set_admin_guc(session)
                    sub = (
                        await session.execute(
                            select(Subscription).where(Subscription.external_id == sub_id)
                        )
                    ).scalar_one_or_none()

                if sub is None:
                    return {"received": True, "type": et, "noop": "subscription not found"}

                tenant_id = sub.tenant_id

                if et == "customer.subscription.deleted":
                    status = SubscriptionStatus.canceled
                    plan = Plan.free
                else:
                    stripe_status = data.get("status", "active")
                    status = _STRIPE_STATUS_MAP.get(stripe_status, SubscriptionStatus.active)

                    if status == SubscriptionStatus.canceled:
                        plan = Plan.free
                    else:
                        plan = None
                        meta_plan = data.get("metadata", {}).get("plan")
                        if meta_plan:
                            try:
                                plan = Plan(meta_plan)
                            except ValueError:
                                plan = None

                        if plan is None:
                            items = data.get("items", {}).get("data", [])
                            if items and isinstance(items, list):
                                price_id = items[0].get("price", {}).get("id")
                                p_map = _plan_by_price()
                                if price_id and price_id in p_map:
                                    plan = p_map[price_id]

                        if plan is None:
                            plan = sub.plan

                await update_tenant_subscription(
                    session,
                    tenant_id,
                    plan=plan,
                    status=status,
                    external_id=sub_id or sub.external_id,
                )
                await session.commit()
            return {
                "received": True,
                "type": et,
                "tenant_id": str(tenant_id),
                "plan": plan.value,
                "status": status.value,
            }

        return {"received": True, "type": et, "noop": True}

