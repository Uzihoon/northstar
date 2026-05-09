"""add itinerary plan runs

Revision ID: a74c2f91d3a8
Revises: 6f4a2c7e1b90
Create Date: 2026-05-07 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a74c2f91d3a8"
down_revision: Union[str, Sequence[str], None] = "6f4a2c7e1b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  op.create_table(
    "itinerary_plan_runs",
    sa.Column("id", sa.String(length=36), nullable=False),
    sa.Column("user_id", sa.String(length=36), nullable=False),
    sa.Column("original_prompt", sa.Text(), nullable=False),
    sa.Column("model_name", sa.String(length=128), nullable=False),
    sa.Column("save", sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column("status", sa.String(length=32), nullable=False),
    sa.Column("progress_events", sa.JSON(), nullable=False),
    sa.Column("error_message", sa.Text(), nullable=True),
    sa.Column("trip_request_id", sa.String(length=36), nullable=True),
    sa.Column("plan_id", sa.String(length=36), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(["plan_id"], ["itinerary_plans.id"]),
    sa.ForeignKeyConstraint(["trip_request_id"], ["trip_requests.id"]),
    sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    sa.PrimaryKeyConstraint("id"),
  )
  op.create_index(
    op.f("ix_itinerary_plan_runs_plan_id"),
    "itinerary_plan_runs",
    ["plan_id"],
    unique=False,
  )
  op.create_index(
    op.f("ix_itinerary_plan_runs_status"),
    "itinerary_plan_runs",
    ["status"],
    unique=False,
  )
  op.create_index(
    op.f("ix_itinerary_plan_runs_trip_request_id"),
    "itinerary_plan_runs",
    ["trip_request_id"],
    unique=False,
  )
  op.create_index(
    op.f("ix_itinerary_plan_runs_user_id"),
    "itinerary_plan_runs",
    ["user_id"],
    unique=False,
  )


def downgrade() -> None:
  op.drop_index(op.f("ix_itinerary_plan_runs_user_id"), table_name="itinerary_plan_runs")
  op.drop_index(op.f("ix_itinerary_plan_runs_trip_request_id"), table_name="itinerary_plan_runs")
  op.drop_index(op.f("ix_itinerary_plan_runs_status"), table_name="itinerary_plan_runs")
  op.drop_index(op.f("ix_itinerary_plan_runs_plan_id"), table_name="itinerary_plan_runs")
  op.drop_table("itinerary_plan_runs")
