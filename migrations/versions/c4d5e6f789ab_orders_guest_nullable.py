"""Orders: nullable user_id for guest checkout, guest_email

Revision ID: c4d5e6f789ab
Revises: b2c3d4e5f67
Create Date: 2026-04-16

"""
from alembic import op
import sqlalchemy as sa


revision = "c4d5e6f789ab"
down_revision = "b2c3d4e5f67"


def upgrade():
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.add_column(sa.Column("guest_email", sa.String(255), nullable=True))
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade():
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_column("guest_email")
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
