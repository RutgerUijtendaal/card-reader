"""initial schema

Revision ID: 20260417_0001
Revises:
Create Date: 2026-04-17 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260417_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "card",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("latest_version_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_card_key", "card", ["key"], unique=True)
    op.create_index("ix_card_latest_version_id", "card", ["latest_version_id"], unique=False)

    op.create_table(
        "import_job",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_path", sa.String(), nullable=False),
        sa.Column("template_id", sa.String(), nullable=False),
        sa.Column("options_json", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("processed_items", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "import_job_item",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("source_file", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_job_item_job_id", "import_job_item", ["job_id"], unique=False)

    op.create_table(
        "card_version",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("card_id", sa.String(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.String(), nullable=False),
        sa.Column("image_hash", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type_line", sa.String(), nullable=False),
        sa.Column("mana_cost", sa.String(), nullable=False),
        sa.Column("mana_symbols_json", sa.String(), nullable=False),
        sa.Column("attack", sa.Integer(), nullable=True),
        sa.Column("health", sa.Integer(), nullable=True),
        sa.Column("rules_text", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("parse_result_id", sa.String(), nullable=True),
        sa.Column("is_latest", sa.Boolean(), nullable=False),
        sa.Column("previous_version_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_card_version_card_id", "card_version", ["card_id"], unique=False)
    op.create_index("ix_card_version_image_hash", "card_version", ["image_hash"], unique=False)
    op.create_index("ix_card_version_is_latest", "card_version", ["is_latest"], unique=False)
    op.create_index("ix_card_version_parse_result_id", "card_version", ["parse_result_id"], unique=False)
    op.create_index("ix_card_version_previous_version_id", "card_version", ["previous_version_id"], unique=False)
    op.create_index("ix_card_version_template_id", "card_version", ["template_id"], unique=False)
    op.create_index("ix_card_version_version_number", "card_version", ["version_number"], unique=False)
    op.create_index("ix_card_version_card_latest", "card_version", ["card_id", "is_latest"], unique=False)
    op.create_index("ux_card_version_card_version", "card_version", ["card_id", "version_number"], unique=True)

    op.create_table(
        "card_version_image",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("card_version_id", sa.String(), nullable=False),
        sa.Column("source_file", sa.String(), nullable=False),
        sa.Column("stored_path", sa.String(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_card_version_image_card_version_id", "card_version_image", ["card_version_id"], unique=False)
    op.create_index("ix_card_version_image_checksum", "card_version_image", ["checksum"], unique=False)

    op.create_table(
        "parse_result",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("card_version_id", sa.String(), nullable=False),
        sa.Column("raw_ocr_json", sa.String(), nullable=False),
        sa.Column("normalized_fields_json", sa.String(), nullable=False),
        sa.Column("confidence_json", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_parse_result_card_version_id", "parse_result", ["card_version_id"], unique=False)

    op.create_table(
        "tag",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tag_key", "tag", ["key"], unique=True)

    op.create_table(
        "symbol",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_symbol_key", "symbol", ["key"], unique=True)

    op.create_table(
        "keyword",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_keyword_key", "keyword", ["key"], unique=True)

    op.create_table(
        "type",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_type_key", "type", ["key"], unique=True)

    op.create_table(
        "card_version_tag",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("card_version_id", sa.String(), nullable=False),
        sa.Column("tag_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_card_version_tag_card_version_id", "card_version_tag", ["card_version_id"], unique=False)
    op.create_index("ix_card_version_tag_tag_id", "card_version_tag", ["tag_id"], unique=False)
    op.create_index("ux_card_version_tag_pair", "card_version_tag", ["card_version_id", "tag_id"], unique=True)

    op.create_table(
        "card_version_symbol",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("card_version_id", sa.String(), nullable=False),
        sa.Column("symbol_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_card_version_symbol_card_version_id", "card_version_symbol", ["card_version_id"], unique=False)
    op.create_index("ix_card_version_symbol_symbol_id", "card_version_symbol", ["symbol_id"], unique=False)
    op.create_index("ux_card_version_symbol_pair", "card_version_symbol", ["card_version_id", "symbol_id"], unique=True)

    op.create_table(
        "card_version_keyword",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("card_version_id", sa.String(), nullable=False),
        sa.Column("keyword_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_card_version_keyword_card_version_id", "card_version_keyword", ["card_version_id"], unique=False)
    op.create_index("ix_card_version_keyword_keyword_id", "card_version_keyword", ["keyword_id"], unique=False)
    op.create_index("ux_card_version_keyword_pair", "card_version_keyword", ["card_version_id", "keyword_id"], unique=True)

    op.create_table(
        "card_version_type",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("card_version_id", sa.String(), nullable=False),
        sa.Column("type_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_card_version_type_card_version_id", "card_version_type", ["card_version_id"], unique=False)
    op.create_index("ix_card_version_type_type_id", "card_version_type", ["type_id"], unique=False)
    op.create_index("ux_card_version_type_pair", "card_version_type", ["card_version_id", "type_id"], unique=True)

    op.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS card_version_search USING fts5(
            card_id UNINDEXED,
            card_version_id UNINDEXED,
            name,
            type_line,
            rules_text,
            mana_cost
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS card_version_search")

    op.drop_index("ux_card_version_type_pair", table_name="card_version_type")
    op.drop_index("ix_card_version_type_type_id", table_name="card_version_type")
    op.drop_index("ix_card_version_type_card_version_id", table_name="card_version_type")
    op.drop_table("card_version_type")

    op.drop_index("ux_card_version_keyword_pair", table_name="card_version_keyword")
    op.drop_index("ix_card_version_keyword_keyword_id", table_name="card_version_keyword")
    op.drop_index("ix_card_version_keyword_card_version_id", table_name="card_version_keyword")
    op.drop_table("card_version_keyword")

    op.drop_index("ux_card_version_symbol_pair", table_name="card_version_symbol")
    op.drop_index("ix_card_version_symbol_symbol_id", table_name="card_version_symbol")
    op.drop_index("ix_card_version_symbol_card_version_id", table_name="card_version_symbol")
    op.drop_table("card_version_symbol")

    op.drop_index("ux_card_version_tag_pair", table_name="card_version_tag")
    op.drop_index("ix_card_version_tag_tag_id", table_name="card_version_tag")
    op.drop_index("ix_card_version_tag_card_version_id", table_name="card_version_tag")
    op.drop_table("card_version_tag")

    op.drop_index("ix_type_key", table_name="type")
    op.drop_table("type")
    op.drop_index("ix_keyword_key", table_name="keyword")
    op.drop_table("keyword")
    op.drop_index("ix_symbol_key", table_name="symbol")
    op.drop_table("symbol")
    op.drop_index("ix_tag_key", table_name="tag")
    op.drop_table("tag")

    op.drop_index("ix_parse_result_card_version_id", table_name="parse_result")
    op.drop_table("parse_result")

    op.drop_index("ix_card_version_image_checksum", table_name="card_version_image")
    op.drop_index("ix_card_version_image_card_version_id", table_name="card_version_image")
    op.drop_table("card_version_image")

    op.drop_index("ux_card_version_card_version", table_name="card_version")
    op.drop_index("ix_card_version_card_latest", table_name="card_version")
    op.drop_index("ix_card_version_version_number", table_name="card_version")
    op.drop_index("ix_card_version_template_id", table_name="card_version")
    op.drop_index("ix_card_version_previous_version_id", table_name="card_version")
    op.drop_index("ix_card_version_parse_result_id", table_name="card_version")
    op.drop_index("ix_card_version_is_latest", table_name="card_version")
    op.drop_index("ix_card_version_image_hash", table_name="card_version")
    op.drop_index("ix_card_version_card_id", table_name="card_version")
    op.drop_table("card_version")

    op.drop_index("ix_import_job_item_job_id", table_name="import_job_item")
    op.drop_table("import_job_item")
    op.drop_table("import_job")

    op.drop_index("ix_card_latest_version_id", table_name="card")
    op.drop_index("ix_card_key", table_name="card")
    op.drop_table("card")
