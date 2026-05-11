"""add source snapshot metadata

Revision ID: f3a91b6c4e22
Revises: d7b8c3f2a901
Create Date: 2026-05-10 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f3a91b6c4e22"
down_revision: Union[str, Sequence[str], None] = "d7b8c3f2a901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  op.add_column(
    "research_source_snapshots",
    sa.Column("source_metadata", sa.JSON(), nullable=True),
  )


def downgrade() -> None:
  op.drop_column("research_source_snapshots", "source_metadata")
