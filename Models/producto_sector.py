from sqlalchemy import Column, Integer, String
from database import Base

class ProductoSector(Base):
    __tablename__ = 'producto_sector'
    producto_codigo = Column(String, primary_key=True)
    sector_id = Column(Integer, primary_key=True)
    unidades = Column(Integer)
