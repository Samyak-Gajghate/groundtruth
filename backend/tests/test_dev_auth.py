from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest

from saas.auth.dev import DevAuthProvider, _encode
from saas.auth.provider import AuthPrincipal
from saas.core.config import settings


@pytest.fixture
def provider() -> DevAuthProvider:
    return DevAuthProvider()


async def test_verify_round_trips(provider: DevAuthProvider) -> None:
    p = AuthPrincipal(user_id=uuid4(), tenant_id=uuid4(), email="x@y.test", is_admin=True)
    tok = _encode(p)
    got = await provider.verify_token(tok)
    assert got == p


async def test_verify_rejects_garbage(provider: DevAuthProvider) -> None:
    assert await provider.verify_token("nope") is None


async def test_verify_rejects_wrong_signature(provider: DevAuthProvider) -> None:
    payload = {
        "sub": str(uuid4()),
        "tenant": str(uuid4()),
        "email": "x@y",
        "admin": True,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()),
    }
    bad = jwt.encode(payload, "wrong-secret", algorithm="HS256")
    assert await provider.verify_token(bad) is None


async def test_verify_rejects_expired(provider: DevAuthProvider) -> None:
    payload = {
        "sub": str(uuid4()),
        "tenant": str(uuid4()),
        "email": "x@y",
        "admin": True,
        "iat": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
        "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
    }
    expired = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    assert await provider.verify_token(expired) is None
