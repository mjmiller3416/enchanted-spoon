"""add OAuth tables for the ChatGPT MCP connector

Revision ID: e1f4a7c2b9d3
Revises: d5b9f3c2e8a4
Create Date: 2026-11-14 19:00:00

Clients from dynamic registration, single-use authorization codes and
access/refresh tokens, all stored as SHA-256 digests (app/models/oauth.py).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f4a7c2b9d3"
down_revision: Union[str, Sequence[str], None] = "d5b9f3c2e8a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create oauth_clients, oauth_authorization_codes and oauth_tokens."""
    op.create_table(
        "oauth_clients",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("client_secret_hash", sa.String(length=64), nullable=True),
        sa.Column("client_name", sa.String(length=255), nullable=True),
        sa.Column("redirect_uris", sa.Text(), nullable=False),
        sa.Column("grant_types", sa.Text(), nullable=False),
        sa.Column("token_endpoint_auth_method", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_oauth_clients_client_id", "oauth_clients", ["client_id"], unique=True)

    op.create_table(
        "oauth_authorization_codes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("grant_id", sa.String(length=64), nullable=False),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("code_challenge", sa.String(length=128), nullable=False),
        sa.Column("scope", sa.String(length=255), nullable=False),
        sa.Column("resource", sa.String(length=2048), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_oauth_authorization_codes_code_hash", "oauth_authorization_codes", ["code_hash"], unique=True
    )
    op.create_index("ix_oauth_authorization_codes_user_id", "oauth_authorization_codes", ["user_id"])
    op.create_index("ix_oauth_authorization_codes_grant_id", "oauth_authorization_codes", ["grant_id"])

    op.create_table(
        "oauth_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("grant_id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope", sa.String(length=255), nullable=False),
        sa.Column("resource", sa.String(length=2048), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_oauth_tokens_token_hash", "oauth_tokens", ["token_hash"], unique=True)
    op.create_index("ix_oauth_tokens_grant_id", "oauth_tokens", ["grant_id"])
    op.create_index("ix_oauth_tokens_user_id", "oauth_tokens", ["user_id"])


def downgrade() -> None:
    """Drop the OAuth tables."""
    op.drop_table("oauth_tokens")
    op.drop_table("oauth_authorization_codes")
    op.drop_table("oauth_clients")
