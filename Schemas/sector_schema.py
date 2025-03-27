from pydantic import BaseModel
from typing import List

class SectorCreate(BaseModel):
    producto: str
    unidades: int

class SectorResponse(SectorCreate):
    id: int

    class Config:
        from_attributes = True

# Esquema de respuesta paginada para sectores
class PaginatedSectorResponse(BaseModel):
    total_registros: int
    por_pagina: int
    pagina_actual: int
    total_paginas: int
    data: List[SectorResponse]
