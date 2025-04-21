from pydantic import BaseModel
from typing import Optional, List
import datetime


class CuentasCreate(BaseModel):
    empresa_id: int
    nombre: str
    email: str
    contraseña: str
    rol: str

class CuentasResponse(CuentasCreate):
    id: int
