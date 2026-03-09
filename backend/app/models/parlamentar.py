from datetime import date

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Casa, TimestampMixin


class Parlamentar(Base, TimestampMixin):
    __tablename__ = "parlamentares"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_externo: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    casa: Mapped[Casa]
    nome_civil: Mapped[str] = mapped_column(String(200))
    nome_parlamentar: Mapped[str] = mapped_column(String(200))
    cpf: Mapped[str | None] = mapped_column(String(11))
    sexo: Mapped[str | None] = mapped_column(String(1))
    data_nascimento: Mapped[date | None]
    uf: Mapped[str] = mapped_column(String(2))
    foto_url: Mapped[str | None] = mapped_column(String(500))
    email: Mapped[str | None] = mapped_column(String(200))
    partido_id: Mapped[int | None] = mapped_column(ForeignKey("partidos.id"))
    legislatura_atual: Mapped[bool] = mapped_column(default=False)
    dados_brutos: Mapped[dict | None] = mapped_column(JSONB)

    partido: Mapped["Partido"] = relationship(back_populates="parlamentares")  # noqa: F821
    votos: Mapped[list["VotoParlamentar"]] = relationship(back_populates="parlamentar")  # noqa: F821
