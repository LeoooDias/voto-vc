import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, ProvedorAuth, TimestampMixin, VotoUsuario


class Usuario(Base, TimestampMixin):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column(String(200), unique=True)
    senha_hash: Mapped[str | None] = mapped_column(String(200))
    nome: Mapped[str | None] = mapped_column(String(200))
    uf: Mapped[str | None] = mapped_column(String(2))
    anonimo: Mapped[bool] = mapped_column(default=True)
    provedor_auth: Mapped[ProvedorAuth] = mapped_column(default=ProvedorAuth.EMAIL)
    provedor_id: Mapped[str | None] = mapped_column(String(200))

    respostas: Mapped[list["RespostaUsuario"]] = relationship(back_populates="usuario")


class RespostaUsuario(Base, TimestampMixin):
    __tablename__ = "respostas_usuarios"
    __table_args__ = (
        UniqueConstraint("usuario_id", "proposicao_id", name="uq_resposta_usuario"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    proposicao_id: Mapped[int] = mapped_column(ForeignKey("proposicoes.id"))
    voto: Mapped[VotoUsuario]
    peso: Mapped[float] = mapped_column(default=1.0)

    usuario: Mapped[Usuario] = relationship(back_populates="respostas")
