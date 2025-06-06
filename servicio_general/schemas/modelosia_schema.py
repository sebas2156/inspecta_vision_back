from pydantic import BaseModel
from typing import Optional, List
import datetime


class ModelosIaCreate(BaseModel):
    nombre: str
    ruta_modelo: str
    classes: str

class ModelosIaResponse(ModelosIaCreate):
    id: int
