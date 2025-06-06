from typing import List, Optional

from sqlalchemy import CHAR, Date, DateTime, ForeignKeyConstraint, Index, String, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
from shared.database import Base

class Camaras(Base):
    __tablename__ = 'camaras'
    __table_args__ = (
        ForeignKeyConstraint(['empresa_id'], ['empresas.id'], onupdate='CASCADE', name='fk_camaras_empresa_id'),
        Index('idx_camaras_empresa_id', 'empresa_id')
    )

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    empresa_id: Mapped[int] = mapped_column(INTEGER(11))
    nombre: Mapped[str] = mapped_column(String(100))
    ip: Mapped[str] = mapped_column(String(39))
    ubicacion: Mapped[str] = mapped_column(String(200))

    empresa: Mapped['Empresas'] = relationship('Empresas', back_populates='camaras')
    regiones: Mapped[List['Regiones']] = relationship('Regiones', back_populates='camara')

