"""add institution and lecturer onboarding

Revision ID: 66a9043e5b42
Revises: 08aff36c2d00
Create Date: 2026-11-01 11:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "66a9043e5b42"
down_revision = "08aff36c2d00"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("requested_role", sa.String(length=30), nullable=True))
    op.add_column("users", sa.Column("requested_staff_number", sa.String(length=50), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "approval_status",
            sa.String(length=30),
            server_default="approved",
            nullable=False,
        ),
    )


def downgrade():
    connection = op.get_bind()
    pending_count = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM users "
            "WHERE approval_status IN ('pending', 'rejected') OR requested_role IS NOT NULL"
        )
    ).scalar_one()
    if pending_count:
        raise RuntimeError(
            "Refusing to remove lecturer onboarding columns while registration requests exist."
        )
    op.drop_column("users", "approval_status")
    op.drop_column("users", "requested_staff_number")
    op.drop_column("users", "requested_role")
