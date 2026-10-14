from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from saas.billing.provider import PLAN_LIMITS
from saas.chat.prompts import SYSTEM_PROMPT, build_user_message
from saas.core.config import settings
from saas.core.llm import claude_stream
from saas.core.logging import get_logger
from saas.core.pricing import chat_cost
from saas.models import (
    Conversation,
    ConversationChannel,
    Message,
    Subscription,
    UsageEvent,
)
from saas.rag.retrieve import retrieve_for_tenant

log = get_logger(__name__)

_MARKER_RE = re.compile(r"\[S(\d+)\]")


class PlanLimitExceeded(RuntimeError):
    pass


async def _check_message_quota(session: AsyncSession, tenant_id: UUID) -> None:
    sub = (
        await session.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
    ).scalar_one_or_none()
    plan = sub.plan if sub else None
    if plan is None:
        return
    limit = PLAN_LIMITS[plan].messages_per_month
    # Month-to-date assistant messages (the billable side).
    used = (
        await session.execute(
            select(func.count(Message.id)).where(
                Message.tenant_id == tenant_id,
                Message.role == "assistant",
                Message.created_at >= func.date_trunc("month", func.now()),
            )
        )
    ).scalar_one()
    if used >= limit:
        raise PlanLimitExceeded(
            f"message limit reached for plan {plan.value}: {used}/{limit}. Upgrade to continue."
        )


async def _check_cost_budget(session: AsyncSession, tenant_id: UUID) -> None:
    sub = (
        await session.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
    ).scalar_one_or_none()
    plan = sub.plan if sub else None
    if plan is None:
        return
    budget = PLAN_LIMITS[plan].cost_budget_usd
    used = (
        await session.execute(
            select(func.coalesce(func.sum(UsageEvent.cost_usd), 0.0)).where(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.created_at >= func.date_trunc("month", func.now()),
            )
        )
    ).scalar_one()
    used_float = float(used)
    if used_float >= budget:
        raise PlanLimitExceeded(
            f"cost budget reached for plan {plan.value}: ${used_float:.4f}/${budget:.2f}. Upgrade to continue."
        )


async def _get_or_create_conversation(
    session: AsyncSession,
    tenant_id: UUID,
    end_user_session: str,
    channel: ConversationChannel,
    conversation_id: UUID | None,
) -> Conversation:
    if conversation_id is not None:
        conv = (
            await session.execute(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.tenant_id == tenant_id,
                )
            )
        ).scalar_one_or_none()
        if conv is not None:
            return conv
    conv = Conversation(
        tenant_id=tenant_id, channel=channel, end_user_session=end_user_session
    )
    session.add(conv)
    await session.flush()
    return conv


async def stream_chat(
    session: AsyncSession,
    tenant_id: UUID,
    user_query: str,
    *,
    end_user_session: str,
    channel: ConversationChannel,
    conversation_id: UUID | None = None,
) -> AsyncIterator[dict[str, str]]:
    """Full SSE event sequence: open -> sources -> token* -> citations -> done.

    Persists the user message and the final assistant message, plus a UsageEvent.
    Raises PlanLimitExceeded before any LLM call if the tenant is over quota."""
    await _check_message_quota(session, tenant_id)
    await _check_cost_budget(session, tenant_id)

    hits = await retrieve_for_tenant(session, tenant_id, user_query)
    conv = await _get_or_create_conversation(
        session, tenant_id, end_user_session, channel, conversation_id
    )

    session.add(
        Message(
            tenant_id=tenant_id,
            conversation_id=conv.id,
            role="user",
            content=user_query,
        )
    )
    await session.commit()

    yield {"event": "open", "data": json.dumps({"conversation_id": str(conv.id)})}
    yield {
        "event": "sources",
        "data": json.dumps(
            {
                "hits": [
                    {
                        "marker": f"S{i + 1}",
                        "chunk_id": str(h.chunk_id),
                        "document_id": str(h.document_id),
                        "filename": h.filename,
                        "snippet": h.content[:280],
                        "similarity": round(h.similarity, 4),
                    }
                    for i, h in enumerate(hits)
                ]
            }
        ),
    }

    user_msg, lookup = build_user_message(user_query, hits)
    collected: list[str] = []
    prompt_tokens, completion_tokens = 0, 0
    async for delta, p_tok, c_tok in claude_stream(
        SYSTEM_PROMPT,
        [{"role": "user", "content": user_msg}],
        max_tokens=800,
        temperature=0.2,
    ):
        if delta:
            collected.append(delta)
            yield {"event": "token", "data": json.dumps({"text": delta})}
        if p_tok is not None and c_tok is not None:
            prompt_tokens, completion_tokens = p_tok, c_tok

    answer = "".join(collected)

    markers_seen: list[str] = []
    seen: set[str] = set()
    for m in _MARKER_RE.finditer(answer):
        mid = f"S{m.group(1)}"
        if mid not in seen:
            markers_seen.append(mid)
            seen.add(mid)

    citations = [
        {
            "marker": m,
            "chunk_id": str(lookup[m].chunk_id),
            "document_id": str(lookup[m].document_id),
            "filename": lookup[m].filename,
            "snippet": lookup[m].content[:280],
        }
        for m in markers_seen
        if m in lookup
    ]
    yield {"event": "citations", "data": json.dumps({"citations": citations})}

    session.add(
        Message(
            tenant_id=tenant_id,
            conversation_id=conv.id,
            role="assistant",
            content=answer,
            citations={"items": citations},
        )
    )
    cost = chat_cost(prompt_tokens, completion_tokens)
    session.add(
        UsageEvent(
            tenant_id=tenant_id,
            kind="chat",
            model=settings.anthropic_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost.total_usd,
        )
    )
    await session.commit()

    yield {
        "event": "done",
        "data": json.dumps(
            {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": cost.total_usd,
            }
        ),
    }
