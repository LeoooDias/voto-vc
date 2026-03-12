import enum
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Casa(str, enum.Enum):
    CAMARA = "camara"
    SENADO = "senado"


class TipoVoto(str, enum.Enum):
    SIM = "sim"
    NAO = "nao"
    ABSTENCAO = "abstencao"
    AUSENTE = "ausente"
    OBSTRUCAO = "obstrucao"
    PRESENTE_SEM_VOTO = "presente_sem_voto"


class VotoUsuario(str, enum.Enum):
    SIM = "sim"
    NAO = "nao"
    PULAR = "pular"


class ProvedorAuth(str, enum.Enum):
    EMAIL = "email"
    GOOGLE = "google"
    MAGIC_LINK = "magic_link"
