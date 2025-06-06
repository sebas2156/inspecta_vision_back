from typing import List, Optional

from sqlalchemy import CHAR, Date, DateTime, ForeignKeyConstraint, Index, String, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
from shared.database import Base

class AlertasEpp(Base):
    __tablename__ = 'alertas_epp'
    __table_args__ = (
        ForeignKeyConstraint(['regla_id'], ['reglas_epp.regla_id'], onupdate='CASCADE', name='fk_alertas_epp_regla_id'),
        Index('fk_alertas_epp_regla_id', 'regla_id'),
        Index('idx_alertas_epp_fecha', 'fecha'),
        Index('idx_alertas_epp_sector_id', 'sector_id')
    )

    id: Mapped[int] = mapped_column(BIGINT(20), primary_key=True)
    regla_id: Mapped[int] = mapped_column(INTEGER(11))
    fecha: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=text('current_timestamp()'))
    sector_id: Mapped[int] = mapped_column(INTEGER(11))
    tipo_incumplimiento: Mapped[str] = mapped_column(String(100))
    imagen: Mapped[str] = mapped_column(String(50))

    regla: Mapped['ReglasEpp'] = relationship('ReglasEpp', back_populates='alertas_epp')

