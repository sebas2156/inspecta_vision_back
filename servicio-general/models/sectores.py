from typing import List, Optional

from sqlalchemy import CHAR, Date, DateTime, ForeignKeyConstraint, Index, String, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
from database import Base

class Sectores(Base):
    __tablename__ = 'sectores'
    __table_args__ = (
        ForeignKeyConstraint(['empresa_id'], ['empresas.id'], onupdate='CASCADE', name='fk_sectores_empresa_id'),
        Index('idx_sectores_empresa_id', 'empresa_id')
    )

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    empresa_id: Mapped[int] = mapped_column(INTEGER(11))

    empresa: Mapped['Empresas'] = relationship('Empresas', back_populates='sectores')
    regiones: Mapped[List['Regiones']] = relationship('Regiones', back_populates='sector')
    reglas_epp: Mapped[List['ReglasEpp']] = relationship('ReglasEpp', back_populates='sector')
    alertas_inventario: Mapped[List['AlertasInventario']] = relationship('AlertasInventario', back_populates='sector')
    producto_sector: Mapped[List['ProductoSector']] = relationship('ProductoSector', back_populates='sector')
    registros_inventario: Mapped[List['RegistrosInventario']] = relationship('RegistrosInventario', back_populates='sector')

