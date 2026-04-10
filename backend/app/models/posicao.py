from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, DirecaoPosicao, TimestampMixin


class Posicao(Base, TimestampMixin):
    __tablename__ = "posicoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    titulo: Mapped[str] = mapped_column(String(200))
    titulo_en: Mapped[str | None] = mapped_column(String(200))
    descricao: Mapped[str] = mapped_column(Text)
    descricao_en: Mapped[str | None] = mapped_column(Text)
    tema: Mapped[str] = mapped_column(String(50))
    ordem: Mapped[int]
    ativo: Mapped[bool] = mapped_column(default=True)

    proposicoes_rel: Mapped[list["PosicaoProposicao"]] = relationship(
        back_populates="posicao", lazy="joined"
    )


class PosicaoProposicao(Base):
    __tablename__ = "posicao_proposicoes"
    __table_args__ = (
        UniqueConstraint("posicao_id", "proposicao_id", name="uq_posicao_proposicao"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    posicao_id: Mapped[int] = mapped_column(ForeignKey("posicoes.id"), index=True)
    proposicao_id: Mapped[int] = mapped_column(ForeignKey("proposicoes.id"))
    direcao: Mapped[DirecaoPosicao]

    posicao: Mapped[Posicao] = relationship(back_populates="proposicoes_rel")
    proposicao: Mapped["Proposicao"] = relationship(lazy="select")  # noqa: F821
