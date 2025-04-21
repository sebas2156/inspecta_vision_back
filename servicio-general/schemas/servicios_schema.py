from pydantic import BaseModel
from typing import Optional, List
import datetime


class ServiciosCreate(BaseModel):
    nombre: str
    descripcion: str

class ServiciosResponse(ServiciosCreate):
    id: int
