from pydantic import BaseModel
from typing import Optional, List
import datetime


class SectoresCreate(BaseModel):
    nombre: str
    empresa_id: int

class SectoresResponse(SectoresCreate):
    id: int
