from __future__ import annotations

import json
import secrets
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from saas.chat.stream import PlanLimitExceeded, stream_chat
from saas.core.logging import get_logger
from saas.db import SessionLocal, set_tenant_guc
from saas.models import ConversationChannel, Tenant
from saas.tenancy.context import set_current_tenant

router = APIRouter(prefix="/widget", tags=["widget"])
log = get_logger(__name__)


async def _tenant_from_public_key(public_key: str) -> Tenant:
    async with SessionLocal() as s:
        # `tenants` is intentionally NOT row-level-secured (it's the directory of
        # tenants; lookup by public_key needs cross-row visibility). Leave the
        # GUC unset — any RLS-protected table touched accidentally here would
        # return zero rows, which is the correct fail-closed behavior.
        await set_tenant_guc(s, None)
        tenant = (
            await s.execute(select(Tenant).where(Tenant.public_key == public_key))
        ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=401, detail="invalid public_key")
    return tenant


class WidgetChatIn(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None  # end-user session id; we mint one if absent
    conversation_id: str | None = None


@router.post("/chat")
async def widget_chat(
    body: WidgetChatIn,
    request: Request,
    public_key: str = Query(min_length=4),
) -> EventSourceResponse:
    tenant = await _tenant_from_public_key(public_key)
    end_user_session = body.session_id or request.cookies.get("wx_session") or secrets.token_urlsafe(16)
    set_current_tenant(tenant.id)

    async def gen() -> AsyncIterator[dict[str, str]]:
        async with SessionLocal() as s:
            await set_tenant_guc(s, str(tenant.id))
            yield {"event": "session", "data": json.dumps({"session_id": end_user_session})}
            try:
                conv_id = None
                if body.conversation_id:
                    from uuid import UUID

                    try:
                        conv_id = UUID(body.conversation_id)
                    except ValueError:
                        conv_id = None
                async for event in stream_chat(
                    s,
                    tenant.id,
                    body.query,
                    end_user_session=end_user_session,
                    channel=ConversationChannel.widget,
                    conversation_id=conv_id,
                ):
                    yield event
            except PlanLimitExceeded as exc:
                yield {"event": "error", "data": json.dumps({"detail": str(exc), "kind": "plan_limit"})}

    resp = EventSourceResponse(gen())
    resp.set_cookie("wx_session", end_user_session, max_age=60 * 60 * 24 * 30, samesite="lax")
    return resp


@router.get("/config")
async def widget_config(public_key: str = Query(min_length=4)) -> dict:
    tenant = await _tenant_from_public_key(public_key)
    return {
        "tenant_name": tenant.name,
        "tenant_slug": tenant.slug,
        "plan": tenant.plan.value,
    }
