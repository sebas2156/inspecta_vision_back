from pydantic import BaseModel
from typing import Optional, List
import datetime


class SuscripcionesCreate(BaseModel):
    empresa_id: int
    servicio_id: int
    fecha_inicio: datetime.date
    fecha_fin: datetime.date
    modelo_id: int

class SuscripcionesResponse(SuscripcionesCreate):
    id: int
