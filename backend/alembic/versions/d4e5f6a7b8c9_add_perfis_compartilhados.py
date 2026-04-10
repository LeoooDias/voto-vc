"""add perfis_compartilhados

Revision ID: d4e5f6a7b8c9
Revises: c8d9e0f1a2b3
Create Date: 2026-04-09 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "perfis_compartilhados",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(12), nullable=False, unique=True, index=True),
        sa.Column("respostas", postgresql.JSONB(), nullable=False),
        sa.Column("resultado_parlamentares", postgresql.JSONB(), nullable=False),
        sa.Column("resultado_partidos", postgresql.JSONB(), nullable=False),
        sa.Column("total_respostas", sa.Integer(), nullable=False),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("perfis_compartilhados")
