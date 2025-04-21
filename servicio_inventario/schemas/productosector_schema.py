from pydantic import BaseModel
from typing import Optional, List
import datetime


class ProductoSectorCreate(BaseModel):
    producto_codigo: str
    empresa_id: int
    sector_id: int
    permitido: str
    stock_minimo: int = None
    stock_maximo: int = None

class ProductoSectorResponse(ProductoSectorCreate):
    id: int

