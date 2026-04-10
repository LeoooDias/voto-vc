from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PerfilCompartilhado(Base, TimestampMixin):
    __tablename__ = "perfis_compartilhados"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    respostas: Mapped[dict] = mapped_column(JSONB)
    resultado_parlamentares: Mapped[list] = mapped_column(JSONB)
    resultado_partidos: Mapped[list] = mapped_column(JSONB)
    total_respostas: Mapped[int]
    ip_hash: Mapped[str | None] = mapped_column(String(64))
