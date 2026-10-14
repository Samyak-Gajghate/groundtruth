from __future__ import annotations

from contextvars import ContextVar
from uuid import UUID

_tenant_id: ContextVar[UUID | None] = ContextVar("tenant_id", default=None)


def set_current_tenant(tid: UUID | None) -> None:
    _tenant_id.set(tid)


def current_tenant() -> UUID | None:
    return _tenant_id.get()


def require_tenant() -> UUID:
    tid = _tenant_id.get()
    if tid is None:
        raise RuntimeError("no tenant in current request context")
    return tid
