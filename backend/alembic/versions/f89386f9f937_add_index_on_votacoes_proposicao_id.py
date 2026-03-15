"""add index on votacoes.proposicao_id

Revision ID: f89386f9f937
Revises: d6a1012c8434
Create Date: 2026-03-15 00:48:50.882916
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f89386f9f937'
down_revision: Union[str, None] = 'd6a1012c8434'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_votacoes_proposicao_id', 'votacoes', ['proposicao_id'])


def downgrade() -> None:
    op.drop_index('ix_votacoes_proposicao_id', 'votacoes')
