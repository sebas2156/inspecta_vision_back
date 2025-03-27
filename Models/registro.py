from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base

class Registro(Base):
    __tablename__ = "registros"
    id = Column(Integer, primary_key=True)
    sector_id = Column(Integer)
    producto_codigo = Column(String(500), primary_key=True)
    accion = Column(String(500))
    fecha = Column(DateTime, default=func.current_timestamp())
