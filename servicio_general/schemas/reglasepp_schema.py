from pydantic import BaseModel
from typing import Optional, List
import datetime


class ReglasEppCreate(BaseModel):
    sector_id: int
    suscripcion_id: int
    restricciones_equipamiento: str

class ReglasEppResponse(ReglasEppCreate):
    regla_id: int
