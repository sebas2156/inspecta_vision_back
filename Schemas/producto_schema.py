from pydantic import BaseModel
from typing import List

class ProductoCreate(BaseModel):
    codigo: str
    nombre_producto: str
    descripcion: str
    categoria: str
    stock: int
    sector: int
    minimo: int

class ProductoResponse(ProductoCreate):
    # El código es la clave primaria, así que no necesitamos 'id'
    class Config:
        from_attributes = True  # Habilitar la conversión automática desde SQLAlchemy ORM

# Esquema de respuesta paginada para productos
class PaginatedProductoResponse(BaseModel):
    total_registros: int
    por_pagina: int
    pagina_actual: int
    total_paginas: int
    data: List[ProductoResponse]
