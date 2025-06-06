from pydantic import BaseModel
from typing import Optional, List
import datetime


class CamarasCreate(BaseModel):
    empresa_id: int
    nombre: str
    ip: str
    ubicacion: str

class CamarasResponse(CamarasCreate):
    id: int

