from typing import List, Optional

from sqlalchemy import CHAR, Date, DateTime, ForeignKeyConstraint, Index, String, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
from shared.database import Base

class ModelosIa(Base):
    __tablename__ = 'modelos_ia'

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    ruta_modelo: Mapped[str] = mapped_column(String(200))
    classes: Mapped[str] = mapped_column(LONGTEXT)

    suscripciones: Mapped[List['Suscripciones']] = relationship('Suscripciones', back_populates='modelo')

