from typing import List, Optional

from sqlalchemy import CHAR, Date, DateTime, ForeignKeyConstraint, Index, String, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
from shared.database import Base

class ReglasEpp(Base):
    __tablename__ = 'reglas_epp'
    __table_args__ = (
        ForeignKeyConstraint(['sector_id'], ['sectores.id'], onupdate='CASCADE', name='fk_reglas_epp_sector_id'),
        ForeignKeyConstraint(['suscripcion_id'], ['suscripciones.id'], onupdate='CASCADE', name='fk_reglas_epp_suscripcion_id'),
        Index('idx_reglas_epp_regla_id_unique', 'regla_id', unique=True),
        Index('idx_reglas_epp_sector_id_suscripcion_id_unique', 'sector_id', 'suscripcion_id', unique=True),
        Index('idx_reglas_epp_suscripcion_id', 'suscripcion_id')
    )

    regla_id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    sector_id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    suscripcion_id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    restricciones_equipamiento: Mapped[str] = mapped_column(LONGTEXT)

    sector: Mapped['Sectores'] = relationship('Sectores', back_populates='reglas_epp')
    suscripcion: Mapped['Suscripciones'] = relationship('Suscripciones', back_populates='reglas_epp')
    alertas_epp: Mapped[List['AlertasEpp']] = relationship('AlertasEpp', back_populates='regla')

