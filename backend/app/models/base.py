import enum
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Casa(enum.StrEnum):
    CAMARA = "camara"
    SENADO = "senado"


class TipoVoto(enum.StrEnum):
    SIM = "sim"
    NAO = "nao"
    ABSTENCAO = "abstencao"
    AUSENTE = "ausente"
    OBSTRUCAO = "obstrucao"
    PRESENTE_SEM_VOTO = "presente_sem_voto"


class VotoUsuario(enum.StrEnum):
    SIM = "sim"
    NAO = "nao"
    PULAR = "pular"


class Orientacao(enum.StrEnum):
    SIM = "sim"
    NAO = "nao"
    ABSTENCAO = "abstencao"
    OBSTRUCAO = "obstrucao"
    LIBERADO = "liberado"


class ProvedorAuth(enum.StrEnum):
    EMAIL = "email"
    GOOGLE = "google"
    MAGIC_LINK = "magic_link"


# Mapeamento de valores brutos do CSV/API para orientação normalizada
ORIENTACAO_NORMALIZADA: dict[str, str] = {
    "Sim": "sim",
    "Favorável": "sim",
    "Não": "nao",
    "Contrário": "nao",
    "Abstenção": "abstencao",
    "Obstrução": "obstrucao",
    "Art. 17": "abstencao",
    "Favorável com restrições": "sim",
    "Liberado": "liberado",
}
