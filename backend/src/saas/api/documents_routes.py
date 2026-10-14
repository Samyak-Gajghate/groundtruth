from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from saas.api.deps import get_principal, tenant_scoped_session
from saas.auth.provider import AuthPrincipal
from saas.models import Chunk, Document
from saas.rag.ingest import IngestError, ingest_pdf

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentOut(BaseModel):
    id: UUID
    filename: str
    byte_size: int
    page_count: int | None
    chunk_count: int
    created_at: str


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    principal: AuthPrincipal = Depends(get_principal),
    session: AsyncSession = Depends(tenant_scoped_session),
) -> list[DocumentOut]:
    rows = (
        await session.execute(
            select(
                Document.id,
                Document.filename,
                Document.byte_size,
                Document.page_count,
                Document.created_at,
                func.count(Chunk.id).label("chunk_count"),
            )
            .outerjoin(Chunk, Chunk.document_id == Document.id)
            .where(Document.tenant_id == principal.tenant_id)
            .group_by(Document.id)
            .order_by(desc(Document.created_at))
        )
    ).all()
    return [
        DocumentOut(
            id=r.id,
            filename=r.filename,
            byte_size=r.byte_size,
            page_count=r.page_count,
            chunk_count=r.chunk_count,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    principal: AuthPrincipal = Depends(get_principal),
    session: AsyncSession = Depends(tenant_scoped_session),
) -> DocumentOut:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="only PDF uploads accepted")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty file")
    try:
        doc = await ingest_pdf(session, principal.tenant_id, file.filename, data)
    except IngestError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    chunk_count = (
        await session.execute(select(func.count(Chunk.id)).where(Chunk.document_id == doc.id))
    ).scalar_one()
    return DocumentOut(
        id=doc.id,
        filename=doc.filename,
        byte_size=doc.byte_size,
        page_count=doc.page_count,
        chunk_count=chunk_count,
        created_at=doc.created_at.isoformat(),
    )


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: UUID,
    principal: AuthPrincipal = Depends(get_principal),
    session: AsyncSession = Depends(tenant_scoped_session),
) -> None:
    doc = (
        await session.execute(
            select(Document).where(Document.id == doc_id, Document.tenant_id == principal.tenant_id)
        )
    ).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="not found")
    await session.delete(doc)
    await session.commit()
