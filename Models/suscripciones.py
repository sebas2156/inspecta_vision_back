from sqlalchemy import Column, Integer, Float, Date
from database import Base

class Suscripciones(Base):
    __tablename__ = 'suscripciones'
    id = Column(Integer, primary_key=True)
    id_empresa = Column(Integer)
    id_servicio = Column(Integer)
    fecha_inicio = Column(Date)
    fecha_fin = Column(Date)
    cantidad_camaras = Column(Integer)
    cantidad_clases = Column(Integer)
    precio = Column(Float)