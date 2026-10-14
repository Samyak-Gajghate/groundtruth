from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from saas.api.deps import get_billing_provider, get_principal, tenant_scoped_session
from saas.auth.provider import AuthPrincipal
from saas.billing.mock import MockBillingProvider
from saas.billing.provider import PLAN_LIMITS, BillingProvider
from saas.models import Message, Plan, Subscription, Tenant, UsageEvent

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutIn(BaseModel):
    plan: Plan
    return_url: str


class CheckoutOut(BaseModel):
    url: str
    session_id: str
    provider: str


@router.get("/plans")
async def plans() -> dict:
    return {
        "plans": [
            {
                "id": p.value,
                "docs": PLAN_LIMITS[p].docs,
                "messages": PLAN_LIMITS[p].messages_per_month,
                "cost_budget_usd": PLAN_LIMITS[p].cost_budget_usd,
            }
            for p in Plan
        ]
    }


@router.get("/me")
async def my_billing(
    principal: AuthPrincipal = Depends(get_principal),
    session: AsyncSession = Depends(tenant_scoped_session),
) -> dict:
    sub = (
        await session.execute(select(Subscription).where(Subscription.tenant_id == principal.tenant_id))
    ).scalar_one()
    used_msgs = (
        await session.execute(
            select(func.count(Message.id)).where(
                Message.tenant_id == principal.tenant_id,
                Message.role == "assistant",
                Message.created_at >= func.date_trunc("month", func.now()),
            )
        )
    ).scalar_one()
    cost_month = (
        await session.execute(
            select(func.coalesce(func.sum(UsageEvent.cost_usd), 0)).where(
                UsageEvent.tenant_id == principal.tenant_id,
                UsageEvent.created_at >= func.date_trunc("month", func.now()),
            )
        )
    ).scalar_one()
    limits = PLAN_LIMITS[sub.plan]
    return {
        "plan": sub.plan.value,
        "status": sub.status.value,
        "limits": {
            "docs": limits.docs,
            "messages": limits.messages_per_month,
            "cost_budget_usd": limits.cost_budget_usd,
        },
        "used_messages_this_month": int(used_msgs),
        "cost_usd_this_month": round(float(cost_month), 4),
    }


@router.post("/checkout", response_model=CheckoutOut)
async def create_checkout(
    body: CheckoutIn,
    principal: AuthPrincipal = Depends(get_principal),
    billing: BillingProvider = Depends(get_billing_provider),
) -> CheckoutOut:
    try:
        cs = await billing.create_checkout(principal.tenant_id, body.plan, body.return_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CheckoutOut(url=cs.url, session_id=cs.session_id, provider=billing.name)


@router.post("/cancel")
async def cancel_subscription(
    principal: AuthPrincipal = Depends(get_principal),
    billing: BillingProvider = Depends(get_billing_provider),
) -> dict:
    await billing.cancel(principal.tenant_id)
    return {"ok": True}


@router.post("/webhook")
async def webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    billing: BillingProvider = Depends(get_billing_provider),
) -> dict:
    body = await request.body()
    return await billing.handle_webhook(body, stripe_signature)


# Mock-only confirm endpoint used by the Next.js mock-checkout page.
class MockConfirmIn(BaseModel):
    session_id: str


@router.post("/mock/confirm")
async def mock_confirm(
    body: MockConfirmIn,
    billing: BillingProvider = Depends(get_billing_provider),
) -> dict:
    if not isinstance(billing, MockBillingProvider):
        raise HTTPException(status_code=400, detail="mock confirm only valid when BILLING_PROVIDER=mock")
    try:
        tenant_id, plan = await billing.confirm_session(body.session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "tenant_id": str(tenant_id),
        "plan": plan.value,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }
