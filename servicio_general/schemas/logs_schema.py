from pydantic import BaseModel
from typing import Optional, List
import datetime


class LogsCreate(BaseModel):
    fecha: datetime.datetime
    cuenta_id: int
    accion: str
    detalles: str

class LogsResponse(LogsCreate):
    id: int

