from typing import List, Optional

from sqlalchemy import CHAR, Date, DateTime, ForeignKeyConstraint, Index, String, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
from shared.database import Base

class Empresas(Base):
    __tablename__ = 'empresas'

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(500))
    email: Mapped[Optional[str]] = mapped_column(String(500))
    telefono: Mapped[Optional[str]] = mapped_column(String(20))

    camaras: Mapped[List['Camaras']] = relationship('Camaras', back_populates='empresa')
    cuentas: Mapped[List['Cuentas']] = relationship('Cuentas', back_populates='empresa')
    sectores: Mapped[List['Sectores']] = relationship('Sectores', back_populates='empresa')
    suscripciones: Mapped[List['Suscripciones']] = relationship('Suscripciones', back_populates='empresa')
    productos: Mapped[List['Productos']] = relationship('Productos', back_populates='empresa')

