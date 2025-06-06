from typing import List, Optional

from sqlalchemy import CHAR, Date, DateTime, ForeignKeyConstraint, Index, String, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
from shared.database import Base

class Servicios(Base):
    __tablename__ = 'servicios'

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    descripcion: Mapped[str] = mapped_column(Text)

    suscripciones: Mapped[List['Suscripciones']] = relationship('Suscripciones', back_populates='servicio')

