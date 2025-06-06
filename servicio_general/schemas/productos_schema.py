from pydantic import BaseModel
from typing import Optional, List


class ProductosCreate(BaseModel):
    codigo: str
    empresa_id: int
    nombre: str
    descripcion: str
    categoria: str
    suscripcion_id: int

class ProductosResponse(ProductosCreate):
    class Config:
        orm_mode = True
