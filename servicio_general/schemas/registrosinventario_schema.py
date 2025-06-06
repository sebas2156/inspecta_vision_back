from pydantic import BaseModel
from typing import Optional, List
import datetime


class RegistrosInventarioCreate(BaseModel):
    fecha: datetime.datetime
    producto_codigo: str
    empresa_id: int
    sector_id: int
    accion: str

class RegistrosInventarioResponse(RegistrosInventarioCreate):
    id: int
