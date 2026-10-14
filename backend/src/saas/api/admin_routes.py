from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from saas.api.deps import get_principal, tenant_scoped_session
from saas.auth.provider import AuthPrincipal
from saas.models import Conversation, Document, Message, UsageEvent

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview")
async def overview(
    principal: AuthPrincipal = Depends(get_principal),
    session: AsyncSession = Depends(tenant_scoped_session),
) -> dict:
    if not principal.is_admin:
        raise HTTPException(status_code=403, detail="admin only")

    docs = (
        await session.execute(
            select(func.count(Document.id)).where(Document.tenant_id == principal.tenant_id)
        )
    ).scalar_one()
    convs = (
        await session.execute(
            select(func.count(Conversation.id)).where(Conversation.tenant_id == principal.tenant_id)
        )
    ).scalar_one()
    msgs = (
        await session.execute(
            select(func.count(Message.id)).where(Message.tenant_id == principal.tenant_id)
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

    # 14-day spend timeseries.
    today = date.today()
    since = today - timedelta(days=13)
    daily = (
        await session.execute(
            select(
                func.date_trunc("day", UsageEvent.created_at).label("day"),
                func.coalesce(func.sum(UsageEvent.cost_usd), 0).label("cost"),
                func.coalesce(func.sum(UsageEvent.prompt_tokens + UsageEvent.completion_tokens), 0).label("tokens"),
            )
            .where(UsageEvent.tenant_id == principal.tenant_id, UsageEvent.created_at >= since)
            .group_by("day")
            .order_by("day")
        )
    ).all()

    return {
        "totals": {
            "documents": int(docs),
            "conversations": int(convs),
            "messages": int(msgs),
            "cost_usd_this_month": round(float(cost_month), 4),
        },
        "daily": [
            {"day": r.day.date().isoformat(), "cost_usd": round(float(r.cost), 4), "tokens": int(r.tokens)}
            for r in daily
        ],
    }
