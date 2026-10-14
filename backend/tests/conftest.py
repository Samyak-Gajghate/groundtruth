from __future__ import annotations

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("AUTH_PROVIDER", "dev")
os.environ.setdefault("BILLING_PROVIDER", "mock")
os.environ.setdefault("JWT_SECRET", "test-secret-please-rotate")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://saas:saas@localhost:5436/saas_test")
