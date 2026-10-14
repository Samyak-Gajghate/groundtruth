from __future__ import annotations

import hashlib
import io
from uuid import UUID

from pypdf import PdfReader
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from saas.billing.provider import PLAN_LIMITS
from saas.core.config import settings
from saas.core.llm import embed_texts
from saas.core.logging import get_logger
from saas.core.pricing import embed_cost
from saas.models import Chunk, Document, Subscription, UsageEvent
from saas.rag.chunking import chunk_text

log = get_logger(__name__)


class IngestError(ValueError):
    pass


def _extract_text(pdf_bytes: bytes) -> tuple[str, int]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception as exc:  # noqa: BLE001
            log.warning("pypdf_page_failed", error=str(exc))
    return "\n\n".join(p.strip() for p in parts if p.strip()), len(reader.pages)


async def _check_plan_limit(session: AsyncSession, tenant_id: UUID) -> None:
    sub = (
        await session.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
    ).scalar_one_or_none()
    plan = sub.plan if sub else None
    if plan is None:
        return
    limit = PLAN_LIMITS[plan].docs
    current = (
        await session.execute(
            select(func.count(Document.id)).where(Document.tenant_id == tenant_id)
        )
    ).scalar_one()
    if current >= limit:
        raise IngestError(
            f"document limit reached for plan {plan.value}: {current}/{limit}. Upgrade to add more."
        )


async def ingest_pdf(
    session: AsyncSession,
    tenant_id: UUID,
    filename: str,
    pdf_bytes: bytes,
) -> Document:
    """Ingest one PDF into the tenant's namespace. Idempotent by (tenant_id, sha256)."""
    await _check_plan_limit(session, tenant_id)

    digest = hashlib.sha256(pdf_bytes).hexdigest()
    existing = (
        await session.execute(
            select(Document).where(
                Document.tenant_id == tenant_id, Document.content_hash == digest
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        log.info("doc_dedup", tenant_id=str(tenant_id), digest=digest[:12])
        return existing

    text, pages = _extract_text(pdf_bytes)
    if not text.strip():
        raise IngestError("PDF contained no extractable text")

    chunks = chunk_text(text)
    if not chunks:
        raise IngestError("chunking produced no chunks")

    doc = Document(
        tenant_id=tenant_id,
        filename=filename,
        content_hash=digest,
        byte_size=len(pdf_bytes),
        page_count=pages,
    )
    session.add(doc)
    await session.flush()

    vectors, tokens = await embed_texts([c.content for c in chunks])
    for ch, vec in zip(chunks, vectors, strict=True):
        session.add(
            Chunk(
                tenant_id=tenant_id,
                document_id=doc.id,
                chunk_index=ch.index,
                content=ch.content,
                token_count=ch.token_count,
                embedding=vec,
            )
        )

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
    log.info(
        "doc_ingested",
        tenant_id=str(tenant_id),
        doc_id=str(doc.id),
        chunks=len(chunks),
        tokens=tokens,
    )
    return doc
