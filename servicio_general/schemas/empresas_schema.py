from pydantic import BaseModel
from typing import Optional, List
import datetime


class EmpresasCreate(BaseModel):
    nombre: str
    email: str = None
    telefono: str = None

class EmpresasResponse(EmpresasCreate):
    id: int
