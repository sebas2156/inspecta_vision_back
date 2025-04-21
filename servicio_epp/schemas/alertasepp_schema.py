from pydantic import BaseModel
from typing import Optional, List
import datetime


class AlertasEppCreate(BaseModel):
    regla_id: int
    fecha: datetime.datetime
    sector_id: int
    tipo_incumplimiento: str
    imagen: str

class AlertasEppResponse(AlertasEppCreate):
    id: int
