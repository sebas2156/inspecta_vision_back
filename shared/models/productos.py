from typing import List, Optional

from sqlalchemy import CHAR, Date, DateTime, ForeignKeyConstraint, Index, String, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
from shared.database import Base

class Productos(Base):
    __tablename__ = 'productos'
    __table_args__ = (
        ForeignKeyConstraint(['empresa_id'], ['empresas.id'], onupdate='CASCADE', name='fk_productos_empresa_id'),
        ForeignKeyConstraint(['suscripcion_id'], ['suscripciones.id'], onupdate='CASCADE', name='fk_productos_suscripcion_id'),
        Index('fk_productos_suscripcion_id', 'suscripcion_id'),
        Index('idx_productos_empresa_id', 'empresa_id')
    )

    codigo: Mapped[str] = mapped_column(String(50), primary_key=True)
    empresa_id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str] = mapped_column(Text)
    categoria: Mapped[str] = mapped_column(String(100))
    suscripcion_id: Mapped[int] = mapped_column(INTEGER(11))

    empresa: Mapped['Empresas'] = relationship('Empresas', back_populates='productos')
    suscripcion: Mapped['Suscripciones'] = relationship('Suscripciones', back_populates='productos')
    alertas_inventario: Mapped[List['AlertasInventario']] = relationship('AlertasInventario', foreign_keys='[AlertasInventario.empresa_id]', back_populates='empresa')
    alertas_inventario_: Mapped[List['AlertasInventario']] = relationship('AlertasInventario', foreign_keys='[AlertasInventario.producto_codigo]', back_populates='productos')
    producto_sector: Mapped[List['ProductoSector']] = relationship('ProductoSector', foreign_keys='[ProductoSector.empresa_id]', back_populates='empresa')
    producto_sector_: Mapped[List['ProductoSector']] = relationship('ProductoSector', foreign_keys='[ProductoSector.producto_codigo]', back_populates='productos')
    registros_inventario: Mapped[List['RegistrosInventario']] = relationship('RegistrosInventario', foreign_keys='[RegistrosInventario.empresa_id]', back_populates='empresa')
    registros_inventario_: Mapped[List['RegistrosInventario']] = relationship('RegistrosInventario', foreign_keys='[RegistrosInventario.producto_codigo]', back_populates='productos')

