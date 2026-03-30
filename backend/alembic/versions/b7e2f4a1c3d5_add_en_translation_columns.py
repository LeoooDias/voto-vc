"""add en translation columns

Revision ID: b7e2f4a1c3d5
Revises: 944ac0d79f97
Create Date: 2026-03-29 22:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e2f4a1c3d5'
down_revision: Union[str, None] = '944ac0d79f97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('posicoes', sa.Column('titulo_en', sa.String(200), nullable=True))
    op.add_column('posicoes', sa.Column('descricao_en', sa.Text(), nullable=True))
    op.add_column('proposicoes', sa.Column('resumo_cidadao_en', sa.Text(), nullable=True))
    op.add_column('proposicoes', sa.Column('descricao_detalhada_en', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('proposicoes', 'descricao_detalhada_en')
    op.drop_column('proposicoes', 'resumo_cidadao_en')
    op.drop_column('posicoes', 'descricao_en')
    op.drop_column('posicoes', 'titulo_en')
