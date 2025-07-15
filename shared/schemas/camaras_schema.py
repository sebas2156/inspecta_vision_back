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

class RegionParaCamaraCreate(BaseModel):
    sector_id: int
    coordenadas: str
    color: Optional[str] = "None"  # opcional
    # camara_id no es necesario aquí porque lo asignas en la vista

class CamaraConRegionesCreate(BaseModel):
    empresa_id: int
    nombre: str
    ip: str
    ubicacion: str
    regiones: List[RegionParaCamaraCreate] = []
