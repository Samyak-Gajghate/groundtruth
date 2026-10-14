from __future__ import annotations

from fastapi import APIRouter

from saas import __version__
from saas.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "auth_provider": settings.auth_provider,
        "billing_provider": settings.billing_provider,
    }
