from sqlalchemy import Column, Integer, String
from database import Base

class Camara(Base):
    __tablename__ = "camaras"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer)
    sector_id = Column(Integer)
    ip = Column(String, unique=True)
    nombre = Column(String)
    funciones = Column(String)
