"""add rag chunks

Revision ID: ebe04d56d47b
Revises: b1da9464a071
Create Date: 2026-05-03 10:47:25.724152
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector


revision: str = "ebe04d56d47b"
down_revision: Union[str, Sequence[str], None] = "b1da9464a071"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  op.create_table(
    "rag_chunks",
    sa.Column("id", sa.String(length=36), nullable=False),
    sa.Column("source_path", sa.Text(), nullable=False),
    sa.Column("chunk_index", sa.Integer(), nullable=False),
    sa.Column("text", sa.Text(), nullable=False),
    sa.Column("chunk_metadata", sa.JSON(), nullable=False),
    sa.Column("embedding", Vector(1024), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint("id"),
  )


def downgrade() -> None:
  op.drop_table("rag_chunks")
