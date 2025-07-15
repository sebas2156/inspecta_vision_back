from pydantic import BaseModel
from typing import Optional, List



class ProductoSectorCreate(BaseModel):
    producto_codigo: str
    empresa_id: int
    sector_id: int
    permitido: int
    stock_minimo: Optional[int] = None
    stock_maximo: Optional[int] = None
    stock: Optional[int] = None

class ProductoSectorResponse(ProductoSectorCreate):
    class Config:
        orm_mode = True

