from pydantic import BaseModel
from typing import Optional, List
import datetime


class ReglasEppCreate(BaseModel):
    regla_id: int
    sector_id: int
    suscripcion_id: int
    restricciones_equipamiento: str

class ReglasEppResponse(ReglasEppCreate):
    id: int
