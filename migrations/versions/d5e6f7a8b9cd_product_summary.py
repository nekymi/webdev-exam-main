"""empty message

Revision ID: d5e6f7a8b9cd
Revises: c4d5e6f789ab
Create Date: 2026-04-22

"""
from alembic import op
import sqlalchemy as sa


revision = "d5e6f7a8b9cd"
down_revision = "c4d5e6f789ab"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products", sa.Column("summary", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("products", "summary")
