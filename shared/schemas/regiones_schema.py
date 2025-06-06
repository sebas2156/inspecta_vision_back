from pydantic import BaseModel
from typing import Optional, List
import datetime


class RegionesCreate(BaseModel):
    camara_id: int
    sector_id: int
    coordenadas: str
    color: str

class RegionesResponse(RegionesCreate):
    id: int
