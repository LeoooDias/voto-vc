"""drop auth tables (usuarios, respostas_usuarios, respostas_posicoes)

Revision ID: c8d9e0f1a2b3
Revises: b7e2f4a1c3d5
Create Date: 2026-04-09 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8d9e0f1a2b3"
down_revision: str = "b7e2f4a1c3d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("respostas_posicoes")
    op.drop_table("respostas_usuarios")
    op.drop_table("usuarios")
    op.execute("DROP TYPE IF EXISTS provedorauth")


def downgrade() -> None:
    # Auth tables are not being restored
    pass
