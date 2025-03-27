from sqlalchemy import Column, Integer, String
from database import Base

class Empresas(Base):
    __tablename__ = 'empresas'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    servicio = Column(Integer, default=None)
    email = Column(String, default=None)
    telefono = Column(Integer, default=None)