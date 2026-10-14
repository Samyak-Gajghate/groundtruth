from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from saas.core.config import settings
from saas.core.llm import embed_query
from saas.core.logging import get_logger
from saas.core.pricing import embed_cost
from saas.models import UsageEvent

log = get_logger(__name__)


@dataclass(frozen=True)
class TenantHit:
    chunk_id: UUID
    document_id: UUID
    filename: str
    content: str
    similarity: float


# RLS guarantees tenant scoping, but we also include `tenant_id = :t` as
# belt-and-braces (and to keep the planner using the tenant index).
_SQL = text(
    """
    SELECT c.id AS chunk_id, c.document_id AS document_id, d.filename AS filename, c.content AS content,
           1 - (c.embedding <=> CAST(:vec AS vector)) AS similarity
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE c.tenant_id = :t
    ORDER BY c.embedding <=> CAST(:vec AS vector)
    LIMIT :k
    """
).bindparams(bindparam("vec"), bindparam("t"), bindparam("k"))


def _vec_lit(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in v) + "]"


async def retrieve_for_tenant(
    session: AsyncSession,
    tenant_id: UUID,
    query: str,
    *,
    top_k: int | None = None,
) -> list[TenantHit]:
    k = top_k or settings.retrieve_top_k
    vec, tokens = await embed_query(query)
    rows = (
        await session.execute(
            _SQL, {"vec": _vec_lit(vec), "t": str(tenant_id), "k": k}
        )
    ).mappings().all()

    session.add(
        UsageEvent(
            tenant_id=tenant_id,
            kind="embed",
            model=settings.openai_embedding_model,
            prompt_tokens=tokens,
            cost_usd=embed_cost(tokens),
        )
    )
    await session.commit()

    return [
        TenantHit(
            chunk_id=r["chunk_id"],
            document_id=r["document_id"],
            filename=r["filename"],
            content=r["content"],
            similarity=float(r["similarity"]),
        )
        for r in rows
    ]
