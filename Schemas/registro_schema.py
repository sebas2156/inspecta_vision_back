from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class RegistroCreate(BaseModel):
    id: int
    sector: int
    producto: str
    accion: str
    fecha: Optional[datetime] = None  # Se puede omitir, ya que se asigna automáticamente

class RegistroResponse(RegistroCreate):
    id: int
    fecha: datetime  # Asegura que se devuelva un valor de fecha en la respuesta

    class Config:
        from_attributes = True

# Esquema de respuesta paginada para registros
class PaginatedRegistroResponse(BaseModel):
    total_registros: int
    por_pagina: int
    pagina_actual: int
    total_paginas: int
    data: List[RegistroResponse]
