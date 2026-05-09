"""add research pipeline tables

Revision ID: d7b8c3f2a901
Revises: a74c2f91d3a8
Create Date: 2026-05-09 09:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d7b8c3f2a901"
down_revision: Union[str, Sequence[str], None] = "a74c2f91d3a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  op.create_table(
    "research_runs",
    sa.Column("id", sa.String(length=36), nullable=False),
    sa.Column("target", sa.JSON(), nullable=False),
    sa.Column("model_name", sa.String(length=128), nullable=False),
    sa.Column("status", sa.String(length=32), nullable=False),
    sa.Column("report", sa.JSON(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint("id"),
  )
  op.create_index(op.f("ix_research_runs_status"), "research_runs", ["status"], unique=False)

  op.create_table(
    "research_source_snapshots",
    sa.Column("id", sa.String(length=36), nullable=False),
    sa.Column("run_id", sa.String(length=36), nullable=False),
    sa.Column("url", sa.Text(), nullable=False),
    sa.Column("title", sa.Text(), nullable=True),
    sa.Column("content_hash", sa.String(length=64), nullable=False),
    sa.Column("extracted_text", sa.Text(), nullable=False),
    sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(["run_id"], ["research_runs.id"]),
    sa.PrimaryKeyConstraint("id"),
  )
  op.create_index(
    op.f("ix_research_source_snapshots_content_hash"),
    "research_source_snapshots",
    ["content_hash"],
    unique=False,
  )
  op.create_index(
    op.f("ix_research_source_snapshots_run_id"),
    "research_source_snapshots",
    ["run_id"],
    unique=False,
  )

  op.create_table(
    "research_candidates",
    sa.Column("id", sa.String(length=36), nullable=False),
    sa.Column("run_id", sa.String(length=36), nullable=False),
    sa.Column("country", sa.String(length=128), nullable=False),
    sa.Column("city", sa.String(length=128), nullable=False),
    sa.Column("category", sa.String(length=64), nullable=False),
    sa.Column("name", sa.Text(), nullable=False),
    sa.Column("area", sa.Text(), nullable=True),
    sa.Column("description", sa.Text(), nullable=False),
    sa.Column("price_level", sa.String(length=32), nullable=False),
    sa.Column("trust_rating", sa.String(length=32), nullable=False),
    sa.Column("source_urls", sa.JSON(), nullable=False),
    sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("candidate_metadata", sa.JSON(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(["run_id"], ["research_runs.id"]),
    sa.PrimaryKeyConstraint("id"),
  )
  op.create_index(op.f("ix_research_candidates_category"), "research_candidates", ["category"], unique=False)
  op.create_index(op.f("ix_research_candidates_city"), "research_candidates", ["city"], unique=False)
  op.create_index(op.f("ix_research_candidates_country"), "research_candidates", ["country"], unique=False)
  op.create_index(op.f("ix_research_candidates_price_level"), "research_candidates", ["price_level"], unique=False)
  op.create_index(op.f("ix_research_candidates_run_id"), "research_candidates", ["run_id"], unique=False)
  op.create_index(op.f("ix_research_candidates_trust_rating"), "research_candidates", ["trust_rating"], unique=False)


def downgrade() -> None:
  op.drop_index(op.f("ix_research_candidates_trust_rating"), table_name="research_candidates")
  op.drop_index(op.f("ix_research_candidates_run_id"), table_name="research_candidates")
  op.drop_index(op.f("ix_research_candidates_price_level"), table_name="research_candidates")
  op.drop_index(op.f("ix_research_candidates_country"), table_name="research_candidates")
  op.drop_index(op.f("ix_research_candidates_city"), table_name="research_candidates")
  op.drop_index(op.f("ix_research_candidates_category"), table_name="research_candidates")
  op.drop_table("research_candidates")
  op.drop_index(op.f("ix_research_source_snapshots_run_id"), table_name="research_source_snapshots")
  op.drop_index(op.f("ix_research_source_snapshots_content_hash"), table_name="research_source_snapshots")
  op.drop_table("research_source_snapshots")
  op.drop_index(op.f("ix_research_runs_status"), table_name="research_runs")
  op.drop_table("research_runs")
