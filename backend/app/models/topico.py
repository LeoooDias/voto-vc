from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Topico(Base):
    __tablename__ = "topicos"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True)
    nome: Mapped[str] = mapped_column(String(100))
    descricao: Mapped[str] = mapped_column(Text)
    icone: Mapped[str | None] = mapped_column(String(10))
    cor: Mapped[str | None] = mapped_column(String(7))  # hex color
    ordem: Mapped[int] = mapped_column(default=0)

    proposicoes: Mapped[list["ProposicaoTopico"]] = relationship(back_populates="topico")


class ProposicaoTopico(Base):
    __tablename__ = "proposicoes_topicos"

    proposicao_id: Mapped[int] = mapped_column(ForeignKey("proposicoes.id"), primary_key=True)
    topico_id: Mapped[int] = mapped_column(ForeignKey("topicos.id"), primary_key=True)
    confianca: Mapped[float] = mapped_column(default=1.0)
    metodo: Mapped[str] = mapped_column(String(20), default="heuristic")

    proposicao: Mapped["Proposicao"] = relationship(back_populates="topicos")  # noqa: F821
    topico: Mapped[Topico] = relationship(back_populates="proposicoes")
