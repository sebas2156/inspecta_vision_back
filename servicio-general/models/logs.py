from typing import List, Optional

from sqlalchemy import CHAR, Date, DateTime, ForeignKeyConstraint, Index, String, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
from database import Base

class Logs(Base):
    __tablename__ = 'logs'
    __table_args__ = (
        ForeignKeyConstraint(['cuenta_id'], ['cuentas.id'], onupdate='CASCADE', name='fk_logs_cuenta_id'),
        Index('idx_logs_cuenta_id', 'cuenta_id')
    )

    id: Mapped[int] = mapped_column(BIGINT(20), primary_key=True)
    fecha: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=text('current_timestamp()'))
    cuenta_id: Mapped[int] = mapped_column(INTEGER(11))
    accion: Mapped[str] = mapped_column(String(100))
    detalles: Mapped[str] = mapped_column(LONGTEXT)

    cuenta: Mapped['Cuentas'] = relationship('Cuentas', back_populates='logs')

