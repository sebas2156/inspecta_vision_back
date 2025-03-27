from sqlalchemy import Column, Integer, Float, Date
from database import Base

class HistorialSuscripciones(Base):
    __tablename__ = 'historial_suscripciones'
    id = Column(Integer, primary_key=True)
    id_empresa = Column(Integer)
    id_servicio = Column(Integer)
    fecha_renovacion = Column(Date)
    precio = Column(Float)
    cantidad_camaras = Column(Integer)
    cantidad_clases = Column(Integer)
    fecha_inicio = Column(Date)
    fecha_fin = Column(Date)
