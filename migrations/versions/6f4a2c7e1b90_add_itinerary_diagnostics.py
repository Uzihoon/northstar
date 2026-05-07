"""add itinerary diagnostics

Revision ID: 6f4a2c7e1b90
Revises: 2c9f6c0a8d21
Create Date: 2026-05-06 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "6f4a2c7e1b90"
down_revision: Union[str, Sequence[str], None] = "2c9f6c0a8d21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  op.add_column(
    "itinerary_plans",
    sa.Column("itinerary_diagnostics", sa.JSON(), nullable=True),
  )


def downgrade() -> None:
  op.drop_column("itinerary_plans", "itinerary_diagnostics")
