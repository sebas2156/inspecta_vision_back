from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class AlertasEppBase(BaseModel):
    regla_id: int
    sector_id: int
    tipo_incumplimiento: str
    imagen: Optional[str] = None  # Ruta del archivo
    imagen_url: Optional[str] = None  # URL completa para acceso
    fecha: Optional[datetime] = None


class AlertasEppCreate(AlertasEppBase):
    # Para creación, la imagen debe venir en base64
    # pero no incluimos imagen_url en la creación
    pass


class AlertasEppResponse(AlertasEppBase):
    id: int

    class Config:
        orm_mode = True