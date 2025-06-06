from typing import List, Optional

from sqlalchemy import CHAR, Date, DateTime, ForeignKeyConstraint, Index, String, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
from shared.database import Base

class Cuentas(Base):
    __tablename__ = 'cuentas'
    __table_args__ = (
        ForeignKeyConstraint(['empresa_id'], ['empresas.id'], onupdate='CASCADE', name='fk_cuentas_empresa_id'),
        Index('email', 'email', unique=True),
        Index('idx_cuentas_email_unique', 'email', unique=True),
        Index('idx_cuentas_empresa_id', 'empresa_id')
    )

    id: Mapped[int] = mapped_column(INTEGER(11), primary_key=True)
    empresa_id: Mapped[int] = mapped_column(INTEGER(11))
    nombre: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200))
    contraseña: Mapped[str] = mapped_column(CHAR(60))
    rol: Mapped[str] = mapped_column(String(50))

    empresa: Mapped['Empresas'] = relationship('Empresas', back_populates='cuentas')
    logs: Mapped[List['Logs']] = relationship('Logs', back_populates='cuenta')

