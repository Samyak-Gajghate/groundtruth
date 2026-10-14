from __future__ import annotations

import json
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from saas.api.deps import get_principal, tenant_scoped_session
from saas.auth.provider import AuthPrincipal
from saas.chat.stream import PlanLimitExceeded, stream_chat
from saas.models import ConversationChannel

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatIn(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    conversation_id: UUID | None = None


@router.post("/stream")
async def chat_stream(
    body: ChatIn,
    principal: AuthPrincipal = Depends(get_principal),
    session: AsyncSession = Depends(tenant_scoped_session),
) -> EventSourceResponse:
    async def gen() -> AsyncIterator[dict[str, str]]:
        try:
            async for event in stream_chat(
                session,
                principal.tenant_id,
                body.query,
                end_user_session=f"user:{principal.user_id}",
                channel=ConversationChannel.dashboard,
                conversation_id=body.conversation_id,
            ):
                yield event
        except PlanLimitExceeded as exc:
            yield {"event": "error", "data": json.dumps({"detail": str(exc), "kind": "plan_limit"})}

    return EventSourceResponse(gen())


@router.get("/_precheck")
async def precheck(
    principal: AuthPrincipal = Depends(get_principal),
) -> dict:
    # Cheap GET so the frontend can verify auth before opening an SSE connection
    # (browsers can't send custom headers on EventSource).
    return {"ok": True, "tenant_id": str(principal.tenant_id)}


@router.get("/conversations")
async def list_conversations(
    principal: AuthPrincipal = Depends(get_principal),
    session: AsyncSession = Depends(tenant_scoped_session),
) -> list[dict]:
    from sqlalchemy import desc, func, select
    from saas.models import Conversation, Message

    rows = (
        await session.execute(
            select(Conversation)
            .where(Conversation.tenant_id == principal.tenant_id)
            .order_by(desc(Conversation.created_at))
            .limit(100)
        )
    ).scalars().all()

    out: list[dict] = []
    for c in rows:
        last = (
            await session.execute(
                select(Message)
                .where(Message.conversation_id == c.id)
                .order_by(desc(Message.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        # COUNT(*) on the DB side — previous version fetched all IDs and counted
        # in Python, which is O(messages) per conversation over the wire.
        count = (
            await session.execute(
                select(func.count(Message.id)).where(Message.conversation_id == c.id)
            )
        ).scalar_one()
        out.append(
            {
                "id": str(c.id),
                "channel": c.channel.value,
                "end_user_session": c.end_user_session,
                "created_at": c.created_at.isoformat(),
                "last_message_at": last.created_at.isoformat() if last else None,
                "last_message_preview": (last.content[:120] if last else None),
                "message_count": int(count),
            }
        )
    return out


@router.get("/conversations/{conversation_id}")
async def conversation_detail(
    conversation_id: UUID,
    principal: AuthPrincipal = Depends(get_principal),
    session: AsyncSession = Depends(tenant_scoped_session),
) -> dict:
    from sqlalchemy import select
    from saas.models import Conversation, Message

    conv = (
        await session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.tenant_id == principal.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="not found")
    msgs = (
        await session.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at)
        )
    ).scalars().all()
    return {
        "id": str(conv.id),
        "channel": conv.channel.value,
        "end_user_session": conv.end_user_session,
        "created_at": conv.created_at.isoformat(),
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "citations": m.citations,
                "created_at": m.created_at.isoformat(),
            }
            for m in msgs
        ],
    }
