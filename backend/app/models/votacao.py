from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Casa, TimestampMixin, TipoVoto


class Votacao(Base, TimestampMixin):
    __tablename__ = "votacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_externo: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    proposicao_id: Mapped[int | None] = mapped_column(ForeignKey("proposicoes.id"))
    casa: Mapped[Casa]
    data: Mapped[datetime]
    descricao: Mapped[str | None] = mapped_column(Text)
    resultado: Mapped[str | None] = mapped_column(String(50))
    total_sim: Mapped[int] = mapped_column(default=0)
    total_nao: Mapped[int] = mapped_column(default=0)
    total_abstencao: Mapped[int] = mapped_column(default=0)
    total_ausente: Mapped[int | None]
    dados_brutos: Mapped[dict | None] = mapped_column(JSONB)

    proposicao: Mapped["Proposicao"] = relationship(back_populates="votacoes")  # noqa: F821
    votos_parlamentares: Mapped[list["VotoParlamentar"]] = relationship(back_populates="votacao")


class VotoParlamentar(Base):
    __tablename__ = "votos_parlamentares"
    __table_args__ = (
        UniqueConstraint("votacao_id", "parlamentar_id", name="uq_voto_parlamentar"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    votacao_id: Mapped[int] = mapped_column(ForeignKey("votacoes.id"), index=True)
    parlamentar_id: Mapped[int] = mapped_column(ForeignKey("parlamentares.id"), index=True)
    voto: Mapped[TipoVoto]
    partido_na_epoca: Mapped[str | None] = mapped_column(String(20))
    dados_brutos: Mapped[dict | None] = mapped_column(JSONB)

    votacao: Mapped[Votacao] = relationship(back_populates="votos_parlamentares")
    parlamentar: Mapped["Parlamentar"] = relationship(back_populates="votos")  # noqa: F821
