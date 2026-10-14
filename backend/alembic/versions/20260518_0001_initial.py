"""initial multi-tenant schema with pgvector + Postgres RLS

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-18 00:00:00
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_RLS_TABLES = (
    "users",
    "documents",
    "chunks",
    "conversations",
    "messages",
    "usage_events",
    "subscriptions",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # SQLAlchemy auto-creates the ENUMs when emitting the first column that references them.
    # Listing values inline is required — without them SA generates CREATE TYPE ... AS ENUM ()
    # which Postgres rejects (and the second column references the same name, so we declare
    # the Enum objects once and reuse via .copy()).
    plan_enum = sa.Enum("free", "pro", "enterprise", name="plan")
    subscription_status_enum = sa.Enum(
        "active", "canceled", "past_due", "trialing", name="subscription_status",
    )
    conversation_channel_enum = sa.Enum("dashboard", "widget", name="conversation_channel")

    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("public_key", sa.String(64), nullable=False, unique=True),
        sa.Column("plan", plan_enum, nullable=False, server_default="free"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "email"),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column(
            "plan",
            sa.Enum("free", "pro", "enterprise", name="plan", create_type=False),
            nullable=False,
            server_default="free",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "active", "canceled", "past_due", "trialing",
                name="subscription_status", create_type=False,
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "content_hash"),
    )
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"])
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])

    op.create_table(
        "chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
    )
    op.create_index("ix_chunks_tenant_id", "chunks", ["tenant_id"])
    op.create_index("ix_chunks_tenant_document", "chunks", ["tenant_id", "document_id"])
    op.create_index(
        "ix_chunks_embedding_hnsw",
        "chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "channel",
            sa.Enum("dashboard", "widget", name="conversation_channel", create_type=False),
            nullable=False,
            server_default="dashboard",
        ),
        sa.Column("end_user_session", sa.String(128), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_conversations_tenant_id", "conversations", ["tenant_id"])
    op.create_index("ix_conversations_end_user_session", "conversations", ["end_user_session"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "conversation_id",
            sa.Uuid(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_messages_tenant_id", "messages", ["tenant_id"])
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    op.create_table(
        "usage_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_usage_events_tenant_id", "usage_events", ["tenant_id"])
    op.create_index("ix_usage_events_created_at", "usage_events", ["created_at"])

    # ----- Row-level security -----
    # Defense in depth: even if application code forgets a tenant_id filter,
    # the policy denies access. The app sets `app.tenant_id` once per request
    # via set_config(..., true) so it scopes to the current transaction.
    # RLS is fail-closed: the GUC must be explicitly set per request. An unset
    # or empty GUC matches zero rows. The only allowed bypass is the explicit
    # sentinel '__bootstrap__', set via set_admin_guc() in app code — used for
    # signup (which inserts the first row of a tenant before any tenant context
    # exists) and other system-level cross-tenant maintenance.
    for tbl in _RLS_TABLES:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {tbl}
            USING (
                tenant_id::text = current_setting('app.tenant_id', true)
                OR current_setting('app.tenant_id', true) = '__bootstrap__'
            )
            WITH CHECK (
                tenant_id::text = current_setting('app.tenant_id', true)
                OR current_setting('app.tenant_id', true) = '__bootstrap__'
            )
            """
        )


def downgrade() -> None:
    for tbl in _RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")

    op.drop_index("ix_usage_events_created_at", table_name="usage_events")
    op.drop_index("ix_usage_events_tenant_id", table_name="usage_events")
    op.drop_table("usage_events")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_index("ix_messages_tenant_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_end_user_session", table_name="conversations")
    op.drop_index("ix_conversations_tenant_id", table_name="conversations")
    op.drop_table("conversations")
    op.drop_index("ix_chunks_embedding_hnsw", table_name="chunks")
    op.drop_index("ix_chunks_tenant_document", table_name="chunks")
    op.drop_index("ix_chunks_tenant_id", table_name="chunks")
    op.drop_table("chunks")
    op.drop_index("ix_documents_content_hash", table_name="documents")
    op.drop_index("ix_documents_tenant_id", table_name="documents")
    op.drop_table("documents")
    op.drop_table("subscriptions")
    op.drop_table("users")
    op.drop_table("tenants")
    op.execute("DROP TYPE IF EXISTS conversation_channel")
    op.execute("DROP TYPE IF EXISTS subscription_status")
    op.execute("DROP TYPE IF EXISTS plan")
    op.execute("DROP EXTENSION IF EXISTS vector")
