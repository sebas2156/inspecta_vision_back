from pydantic import BaseModel
from typing import List

class CamaraCreate(BaseModel):
    empresa: str
    ip: str
    nombre: str
    funciones: str

class CamaraResponse(CamaraCreate):
    id: int

    class Config:
        from_attributes = True

# Esquema de respuesta paginada para cámaras
class PaginatedCamaraResponse(BaseModel):
    total_registros: int
    por_pagina: int
    pagina_actual: int
    total_paginas: int
    data: List[CamaraResponse]
