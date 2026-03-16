"""add orientacoes_bancada and update blocos_parlamentares

Revision ID: a1b2c3d4e5f6
Revises: f89386f9f937
Create Date: 2026-03-16 19:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f89386f9f937"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to blocos_parlamentares
    op.add_column(
        "blocos_parlamentares",
        sa.Column("federacao", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "blocos_parlamentares",
        sa.Column("uri", sa.Text(), nullable=True),
    )
    op.add_column(
        "blocos_parlamentares",
        sa.Column("sigla_csv", sa.String(length=100), nullable=True),
    )
    op.create_index("ix_blocos_parlamentares_sigla_csv", "blocos_parlamentares", ["sigla_csv"])

    # Create orientacao enum (DO block handles "already exists" gracefully)
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE orientacao AS ENUM ('sim', 'nao', 'abstencao', 'obstrucao', 'liberado'); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )
    orientacao_enum = sa.Enum("sim", "nao", "abstencao", "obstrucao", "liberado", name="orientacao")

    # Create orientacoes_bancada table
    op.create_table(
        "orientacoes_bancada",
        sa.Column("id_votacao", sa.String(length=50), nullable=False),
        sa.Column("sigla_bancada", sa.String(length=100), nullable=False),
        sa.Column("uri_bancada", sa.Text(), nullable=True),
        sa.Column("orientacao_raw", sa.String(length=50), nullable=False),
        sa.Column("orientacao", orientacao_enum, nullable=False),
        sa.Column("sigla_orgao", sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint("id_votacao", "sigla_bancada"),
    )
    op.create_index("idx_orientacoes_votacao", "orientacoes_bancada", ["id_votacao"])
    op.create_index("idx_orientacoes_bancada", "orientacoes_bancada", ["sigla_bancada"])


def downgrade() -> None:
    op.drop_index("idx_orientacoes_bancada", "orientacoes_bancada")
    op.drop_index("idx_orientacoes_votacao", "orientacoes_bancada")
    op.drop_table("orientacoes_bancada")

    op.execute("DROP TYPE IF EXISTS orientacao")

    op.drop_index("ix_blocos_parlamentares_sigla_csv", "blocos_parlamentares")
    op.drop_column("blocos_parlamentares", "sigla_csv")
    op.drop_column("blocos_parlamentares", "uri")
    op.drop_column("blocos_parlamentares", "federacao")
