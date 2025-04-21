from pydantic import BaseModel
from typing import Optional, List
import datetime


class AlertasInventarioCreate(BaseModel):
    regla_id: int
    fecha: datetime.datetime
    sector_id: int
    producto_codigo: str
    empresa_id: int
    tipo_alerta: str
    imagen: str

class AlertasInventarioResponse(AlertasInventarioCreate):
    id: int
