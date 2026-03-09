from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Casa, TimestampMixin


class Proposicao(Base, TimestampMixin):
    __tablename__ = "proposicoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_externo: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    casa_origem: Mapped[Casa]
    tipo: Mapped[str] = mapped_column(String(20))  # PL, PEC, MPV, PLP, PDL...
    numero: Mapped[int]
    ano: Mapped[int]
    ementa: Mapped[str] = mapped_column(Text)
    ementa_simplificada: Mapped[str | None] = mapped_column(Text)
    resumo_cidadao: Mapped[str | None] = mapped_column(Text)
    url_inteiro_teor: Mapped[str | None] = mapped_column(String(500))
    situacao: Mapped[str | None] = mapped_column(String(100))
    relevancia_score: Mapped[float | None]
    dados_brutos: Mapped[dict | None] = mapped_column(JSONB)

    votacoes: Mapped[list["Votacao"]] = relationship(back_populates="proposicao")  # noqa: F821
    topicos: Mapped[list["ProposicaoTopico"]] = relationship(back_populates="proposicao")  # noqa: F821
