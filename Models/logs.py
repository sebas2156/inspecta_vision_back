from sqlalchemy import Column, Integer, String, Date
from database import Base

class Logs(Base):
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True)
    cuenta_id = Column(Integer)
    accion = Column(String)
    fecha = Column(Date)