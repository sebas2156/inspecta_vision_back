from pydantic import BaseModel
from typing import Optional, List
import datetime


class CuentasCreate(BaseModel):
    empresa_id: int
    nombre: str
    email: str
    contraseña: str
    rol: str


class CuentasResponse(CuentasCreate):
    id: int


# Nuevos esquemas para login
class LoginRequest(BaseModel):
    email: str
    contraseña: str


class LoginResponse(BaseModel):
    nombre: str
    rol: str