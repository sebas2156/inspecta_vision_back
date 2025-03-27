from pydantic import BaseModel
from typing import List

class RegionCreate(BaseModel):
    puntos: str
    color: str
    sector: int

class RegionResponse(RegionCreate):
    id: int

    class Config:
        from_attributes = True

# Esquema de respuesta paginada para regiones
class PaginatedRegionResponse(BaseModel):
    total_registros: int
    por_pagina: int
    pagina_actual: int
    total_paginas: int
    data: List[RegionResponse]
