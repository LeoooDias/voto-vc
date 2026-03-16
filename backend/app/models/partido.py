from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Casa, Orientacao, TimestampMixin

bloco_partido = Table(
    "bloco_partido",
    Base.metadata,
    Column("bloco_id", Integer, ForeignKey("blocos_parlamentares.id"), primary_key=True),
    Column("partido_id", Integer, ForeignKey("partidos.id"), primary_key=True),
)


class Partido(Base, TimestampMixin):
    __tablename__ = "partidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    sigla: Mapped[str] = mapped_column(String(20), unique=True)
    nome: Mapped[str] = mapped_column(String(200))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    dados_brutos: Mapped[dict | None] = mapped_column(JSONB)

    parlamentares: Mapped[list["Parlamentar"]] = relationship(back_populates="partido")  # noqa: F821


class BlocoParlamentar(Base, TimestampMixin):
    __tablename__ = "blocos_parlamentares"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    casa: Mapped[Casa]
    legislatura: Mapped[int]
    federacao: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    uri: Mapped[str | None] = mapped_column(Text)
    sigla_csv: Mapped[str | None] = mapped_column(String(100), index=True)

    partidos: Mapped[list[Partido]] = relationship(secondary=bloco_partido)


class OrientacaoBancada(Base):
    __tablename__ = "orientacoes_bancada"

    id_votacao: Mapped[str] = mapped_column(String(50), primary_key=True)
    sigla_bancada: Mapped[str] = mapped_column(String(100), primary_key=True)
    uri_bancada: Mapped[str | None] = mapped_column(Text)
    orientacao_raw: Mapped[str] = mapped_column(String(50))
    orientacao: Mapped[Orientacao]
    sigla_orgao: Mapped[str | None] = mapped_column(String(20))
