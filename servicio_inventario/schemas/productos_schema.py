from pydantic import BaseModel
from typing import Optional, List
import datetime


class ProductosCreate(BaseModel):
    codigo: str
    empresa_id: int
    nombre: str
    descripcion: str
    categoria: str
    suscripcion_id: int

class ProductosResponse(ProductosCreate):
    id: int
