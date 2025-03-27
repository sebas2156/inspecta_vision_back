from sqlalchemy import Column, Integer, String
from database import Base

class Producto(Base):
    __tablename__ = "productos"

    codigo = Column(String, primary_key=True)
    nombre_producto = Column(String)
    descripcion = Column(String)
    categoria = Column(String)
    stock = Column(Integer)
    sector = Column(Integer)
    minimo = Column(String)
