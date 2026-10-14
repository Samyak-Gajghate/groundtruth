"""Create two demo tenants with distinct docs for the isolation demo:

    acme.com  / admin@acme.com   / password: acmedemo1!
    globex.io / admin@globex.io  / password: globexdemo1!

Each tenant gets a tiny support corpus relevant to ITS product, so the chat
visibly answers differently per tenant. After running, log in as each admin to
verify Acme can't see Globex's docs and vice versa.
"""
from __future__ import annotations

import asyncio
import hashlib

from saas.auth.dev import DevAuthProvider
from saas.core.config import settings
from saas.core.llm import embed_texts
from saas.core.logging import configure_logging, get_logger
from saas.core.pricing import embed_cost
from saas.db import SessionLocal, set_tenant_guc
from saas.models import Chunk, Document, UsageEvent
from saas.rag.chunking import chunk_text

configure_logging()
log = get_logger("seed")


_ACME_DOCS = [
    (
        "billing-faq.txt",
        "Acme Robotics — Billing FAQ\n\n"
        "Customers are billed monthly on the 1st. Invoices are sent to the billing "
        "email on the account. Refunds for unused subscription days are issued within 7 "
        "business days. Contact billing@acme.example to update payment methods.",
    ),
    (
        "warranty.txt",
        "Acme Robotics — Warranty Terms\n\n"
        "All Acme robots ship with a 24-month limited warranty covering manufacturing "
        "defects. The warranty does not cover damage from liquid ingress or unauthorized "
        "modification of the firmware. RMA requests must include the unit serial number "
        "printed on the bottom of the base plate.",
    ),
]

_GLOBEX_DOCS = [
    (
        "delivery.txt",
        "Globex Logistics — Delivery Windows\n\n"
        "Standard delivery is 2-3 business days from dispatch. Express is next business "
        "day for orders placed before 14:00 UTC. We deliver to 38 countries; rural "
        "addresses in Tier 2 markets may add 1-2 days.",
    ),
    (
        "returns.txt",
        "Globex Logistics — Returns Policy\n\n"
        "Returns are accepted within 30 days of delivery. Items must be unused and in "
        "original packaging. Initiate a return from the order page in your account; we "
        "send a prepaid label. Refunds appear within 5 business days after we receive the "
        "package at our hub.",
    ),
]


async def _seed_tenant(email: str, password: str, tenant_name: str, docs: list[tuple[str, str]]) -> None:
    auth = DevAuthProvider()
    try:
        principal, _token = await auth.signup(email, password, tenant_name)
    except ValueError as exc:
        log.warning("signup_skipped", email=email, reason=str(exc))
        principal, _token = await auth.login(email, password)

    async with SessionLocal() as session:
        await set_tenant_guc(session, str(principal.tenant_id))
        for filename, body in docs:
            digest = hashlib.sha256(body.encode()).hexdigest()
            existing_check = await session.execute(
                Document.__table__.select().where(
                    Document.content_hash == digest,
                    Document.tenant_id == principal.tenant_id,
                )
            )
            if existing_check.first() is not None:
                log.info("doc_exists", tenant=tenant_name, filename=filename)
                continue
            doc = Document(
                tenant_id=principal.tenant_id,
                filename=filename,
                content_hash=digest,
                byte_size=len(body),
                page_count=1,
            )
            session.add(doc)
            await session.flush()

            chunks = chunk_text(body)
            vectors, tokens = await embed_texts([c.content for c in chunks])
            for ch, vec in zip(chunks, vectors, strict=True):
                session.add(
                    Chunk(
                        tenant_id=principal.tenant_id,
                        document_id=doc.id,
                        chunk_index=ch.index,
                        content=ch.content,
                        token_count=ch.token_count,
                        embedding=vec,
                    )
                )
            session.add(
                UsageEvent(
                    tenant_id=principal.tenant_id,
                    kind="embed",
                    model=settings.openai_embedding_model,
                    prompt_tokens=tokens,
                    cost_usd=embed_cost(tokens),
                )
            )
            log.info("doc_seeded", tenant=tenant_name, filename=filename, chunks=len(chunks))
        await session.commit()


async def main() -> None:
    await _seed_tenant("admin@acme.example", "acmedemo1!", "Acme Robotics", _ACME_DOCS)
    await _seed_tenant("admin@globex.example", "globexdemo1!", "Globex Logistics", _GLOBEX_DOCS)
    log.info(
        "seed_complete",
        hint="login as admin@acme.example / acmedemo1! or admin@globex.example / globexdemo1!",
    )


if __name__ == "__main__":
    asyncio.run(main())
