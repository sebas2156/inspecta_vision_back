from sqlalchemy import Column, Integer, String
from database import Base

class Cuenta(Base):
    __tablename__ = "cuentas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    correo = Column(String)
    contraseña = Column(String)
    telefono = Column(Integer)
    nivel = Column(String)
    empresa = Column(String)
