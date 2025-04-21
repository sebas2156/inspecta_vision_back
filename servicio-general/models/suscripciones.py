from typing import List, Optional

from sqlalchemy import CHAR, Date, DateTime, ForeignKeyConstraint, Index, String, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
from database import Base

class Suscripciones(Base):
    __tablename__ = 'suscripciones'
    __table_args__ = (
        ForeignKeyConstraint(['empresa_id'], ['empresas.id'], onupdate='CASCADE', name='fk_suscripciones_empresa_id'),
        ForeignKeyConstraint(['modelo_id'], ['modelos_ia.id'], onupdate='CASCADE', name='fk_suscripciones_modelo_id'),
        ForeignKeyConstraint(['servicio_id'], ['servicios.id'], onupdate='CASCADE', name='fk_suscripciones_servicio_id'),
        Index('fk_suscripciones_modelo_id', 'modelo_id'),
        Index('idx_suscripciones_empresa_id', 'empresa_id'),
        Index('idx_suscripciones_servicio_id', 'servicio_id')
    )

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    empresa_id: Mapped[int] = mapped_column(INTEGER(11))
    servicio_id: Mapped[int] = mapped_column(INTEGER(11))
    fecha_inicio: Mapped[datetime.date] = mapped_column(Date)
    fecha_fin: Mapped[datetime.date] = mapped_column(Date)
    modelo_id: Mapped[int] = mapped_column(INTEGER(11))

    empresa: Mapped['Empresas'] = relationship('Empresas', back_populates='suscripciones')
    modelo: Mapped['ModelosIa'] = relationship('ModelosIa', back_populates='suscripciones')
    servicio: Mapped['Servicios'] = relationship('Servicios', back_populates='suscripciones')
    productos: Mapped[List['Productos']] = relationship('Productos', back_populates='suscripcion')
    reglas_epp: Mapped[List['ReglasEpp']] = relationship('ReglasEpp', back_populates='suscripcion')

