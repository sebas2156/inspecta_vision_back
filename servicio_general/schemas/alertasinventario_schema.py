from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class AlertasInventarioBase(BaseModel):
    sector_id: int
    producto_codigo: str
    empresa_id: int
    tipo_alerta: str
    imagen: Optional[str] = None  # Ruta del archivo
    imagen_url: Optional[str] = None  # URL completa para acceso
    fecha: Optional[datetime] = None


class AlertasInventarioCreate(AlertasInventarioBase):
    # Para creación, la imagen debe venir en base64
    # pero no incluimos imagen_url en la creación
    pass


class AlertasInventarioResponse(AlertasInventarioBase):
    id: int

    class Config:
        orm_mode = True