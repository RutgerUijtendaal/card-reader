"""add symbol symbol_type field

Revision ID: 20260419_0003
Revises: 20260419_0002
Create Date: 2026-04-19 00:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260419_0003"
down_revision = "20260419_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "symbol",
        sa.Column("symbol_type", sa.String(), nullable=False, server_default="generic"),
    )
    op.create_index("ix_symbol_symbol_type", "symbol", ["symbol_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_symbol_symbol_type", table_name="symbol")
    op.drop_column("symbol", "symbol_type")

