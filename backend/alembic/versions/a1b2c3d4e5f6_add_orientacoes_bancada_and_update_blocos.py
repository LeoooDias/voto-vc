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

    # Create orientacao enum — use DO block so it's idempotent
    # (Base.metadata may auto-create it via before_create events on earlier migrations)
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE orientacao AS ENUM ('SIM', 'NAO', 'ABSTENCAO', 'OBSTRUCAO', 'LIBERADO'); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )

    # Create orientacoes_bancada table using raw SQL to avoid
    # SQLAlchemy's sa.Enum triggering a duplicate CREATE TYPE
    op.execute(
        "CREATE TABLE orientacoes_bancada ("
        "id_votacao VARCHAR(50) NOT NULL, "
        "sigla_bancada VARCHAR(100) NOT NULL, "
        "uri_bancada TEXT, "
        "orientacao_raw VARCHAR(50) NOT NULL, "
        "orientacao orientacao NOT NULL, "
        "sigla_orgao VARCHAR(20), "
        "PRIMARY KEY (id_votacao, sigla_bancada))"
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
