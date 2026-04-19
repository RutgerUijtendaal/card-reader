"""add symbol detection fields

Revision ID: 20260419_0002
Revises: 20260417_0001
Create Date: 2026-04-19 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260419_0002"
down_revision = "20260417_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "symbol",
        sa.Column("detector_type", sa.String(), nullable=False, server_default="template"),
    )
    op.add_column(
        "symbol",
        sa.Column("detection_config_json", sa.String(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "symbol",
        sa.Column("reference_assets_json", sa.String(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "symbol",
        sa.Column("text_token", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "symbol",
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_symbol_detector_type", "symbol", ["detector_type"], unique=False)
    op.create_index("ix_symbol_enabled", "symbol", ["enabled"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_symbol_enabled", table_name="symbol")
    op.drop_index("ix_symbol_detector_type", table_name="symbol")
    op.drop_column("symbol", "enabled")
    op.drop_column("symbol", "text_token")
    op.drop_column("symbol", "reference_assets_json")
    op.drop_column("symbol", "detection_config_json")
    op.drop_column("symbol", "detector_type")
