from pydantic import BaseModel
from typing import List, Optional

class CuentaCreate(BaseModel):
    nombre: str
    correo: str
    contraseña: str
    telefono: Optional[int] = None
    nivel: str
    empresa: str

class CuentaResponse(CuentaCreate):
    id: int

    class Config:
        from_attributes = True

# Esquema de respuesta paginada para cuentas
class PaginatedCuentaResponse(BaseModel):
    total_registros: int
    por_pagina: int
    pagina_actual: int
    total_paginas: int
    data: List[CuentaResponse]
