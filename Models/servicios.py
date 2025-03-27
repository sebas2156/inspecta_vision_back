from sqlalchemy import Column, Integer, String
from database import Base

class Servicios(Base):
    __tablename__ = 'servicios'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    descripcion = String