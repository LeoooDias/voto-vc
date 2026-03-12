"""add provedor_auth and provedor_id to usuarios

Revision ID: d6a1012c8434
Revises: 75fdf91a7553
Create Date: 2026-03-11 21:26:50.523522
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6a1012c8434'
down_revision: Union[str, None] = '75fdf91a7553'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    provedorauth = sa.Enum('EMAIL', 'GOOGLE', 'MAGIC_LINK', name='provedorauth')
    provedorauth.create(op.get_bind(), checkfirst=True)
    op.add_column('usuarios', sa.Column('provedor_auth', provedorauth, nullable=False, server_default='EMAIL'))
    op.add_column('usuarios', sa.Column('provedor_id', sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column('usuarios', 'provedor_id')
    op.drop_column('usuarios', 'provedor_auth')
    sa.Enum(name='provedorauth').drop(op.get_bind(), checkfirst=True)
