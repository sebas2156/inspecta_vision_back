from typing import List, Optional

from sqlalchemy import CHAR, Date, DateTime, ForeignKeyConstraint, Index, String, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
from database import Base

class Regiones(Base):
    __tablename__ = 'regiones'
    __table_args__ = (
        ForeignKeyConstraint(['camara_id'], ['camaras.id'], onupdate='CASCADE', name='fk_regiones_camara_id'),
        ForeignKeyConstraint(['sector_id'], ['sectores.id'], onupdate='CASCADE', name='fk_regiones_sector_id'),
        Index('idx_regiones_camara_id', 'camara_id'),
        Index('idx_regiones_sector_id', 'sector_id')
    )

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    camara_id: Mapped[int] = mapped_column(INTEGER(11))
    sector_id: Mapped[int] = mapped_column(INTEGER(11))
    coordenadas: Mapped[str] = mapped_column(String(35))
    color: Mapped[str] = mapped_column(String(10))

    camara: Mapped['Camaras'] = relationship('Camaras', back_populates='regiones')
    sector: Mapped['Sectores'] = relationship('Sectores', back_populates='regiones')

