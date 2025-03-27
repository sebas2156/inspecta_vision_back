from sqlalchemy import Column, Integer, String
from database import Base

class Sector(Base):
    __tablename__ = 'sector'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    empresa_id = Column(Integer)
