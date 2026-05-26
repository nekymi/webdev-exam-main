"""Add product_images table

Revision ID: b2c3d4e5f67
Revises: a1b2c3d4e5f6
Create Date: 2025-02-17

"""
from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f67"
down_revision = "a1b2c3d4e5f6"


def upgrade():
    op.create_table(
        "product_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("alt_text", sa.String(255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_main", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("product_images")
