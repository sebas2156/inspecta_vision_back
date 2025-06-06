from typing import List, Optional

from sqlalchemy import CHAR, Date, DateTime, ForeignKeyConstraint, Index, String, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
from shared.database import Base

class RegistrosInventario(Base):
    __tablename__ = 'registros_inventario'
    __table_args__ = (
        ForeignKeyConstraint(['empresa_id'], ['productos.empresa_id'], onupdate='CASCADE', name='fk_registros_inventario_empresa_id'),
        ForeignKeyConstraint(['producto_codigo'], ['productos.codigo'], onupdate='CASCADE', name='fk_registros_inventario_producto_codigo'),
        ForeignKeyConstraint(['sector_id'], ['sectores.id'], onupdate='CASCADE', name='fk_registros_inventario_sector_id'),
        Index('idx_registros_inventario_empresa_id', 'empresa_id'),
        Index('idx_registros_inventario_producto_codigo_empresa_id', 'producto_codigo', 'empresa_id'),
        Index('idx_registros_inventario_sector_id', 'sector_id')
    )

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    fecha: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=text('current_timestamp()'))
    producto_codigo: Mapped[str] = mapped_column(String(50))
    empresa_id: Mapped[int] = mapped_column(INTEGER(11))
    sector_id: Mapped[int] = mapped_column(INTEGER(11))
    accion: Mapped[str] = mapped_column(String(255))

    empresa: Mapped['Productos'] = relationship('Productos', foreign_keys=[empresa_id], back_populates='registros_inventario')
    productos: Mapped['Productos'] = relationship('Productos', foreign_keys=[producto_codigo], back_populates='registros_inventario_')
    sector: Mapped['Sectores'] = relationship('Sectores', back_populates='registros_inventario')
