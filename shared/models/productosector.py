from typing import List, Optional

from sqlalchemy import CHAR, Date, DateTime, ForeignKeyConstraint, Index, String, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
from shared.database import Base

class ProductoSector(Base):
    __tablename__ = 'producto_sector'
    __table_args__ = (
        ForeignKeyConstraint(['empresa_id'], ['productos.empresa_id'], onupdate='CASCADE', name='fk_producto_sector_empresa_id'),
        ForeignKeyConstraint(['producto_codigo'], ['productos.codigo'], onupdate='CASCADE', name='fk_producto_sector_producto_codigo'),
        ForeignKeyConstraint(['sector_id'], ['sectores.id'], onupdate='CASCADE', name='fk_producto_sector_sector_id'),
        Index('idx_producto_sector_empresa_id', 'empresa_id'),
        Index('idx_producto_sector_sector_id', 'sector_id')
    )

    producto_codigo: Mapped[str] = mapped_column(String(50), primary_key=True)
    empresa_id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    sector_id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    permitido: Mapped[int] = mapped_column(TINYINT(4), server_default=text('1'))
    stock_minimo: Mapped[Optional[int]] = mapped_column(INTEGER(11), server_default=text('0'))
    stock_maximo: Mapped[Optional[int]] = mapped_column(INTEGER(11), server_default=text('9999'))

    empresa: Mapped['Productos'] = relationship('Productos', foreign_keys=[empresa_id], back_populates='producto_sector')
    productos: Mapped['Productos'] = relationship('Productos', foreign_keys=[producto_codigo], back_populates='producto_sector_')
    sector: Mapped['Sectores'] = relationship('Sectores', back_populates='producto_sector')

