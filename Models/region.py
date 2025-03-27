from sqlalchemy import Column, Integer, String
from database import Base

class Region(Base):
    __tablename__ = "regiones"

    id = Column(Integer, primary_key=True, index=True)
    puntos = Column(String)
    color = Column(String)
    sector = Column(Integer)
