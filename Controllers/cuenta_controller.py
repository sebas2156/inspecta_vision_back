from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db  # Asumiendo que tienes esta función para obtener la sesión de la DB
from Models.cuenta import Cuenta  # Tu modelo de Cuenta
from Schemas.cuenta_schema import CuentaCreate, CuentaResponse, PaginatedCuentaResponse  # Los esquemas de Pydantic

router = APIRouter()


# Ruta para crear una nueva cuenta
@router.post("/", response_model=CuentaResponse)
def crear_cuenta(cuenta: CuentaCreate, db: Session = Depends(get_db)):
    # Verificamos si la cuenta con el mismo correo ya existe
    existing_cuenta = db.query(Cuenta).filter(Cuenta.correo == cuenta.correo).first()
    if existing_cuenta:
        raise HTTPException(status_code=400, detail="La cuenta con ese correo ya existe.")

    # Creamos la nueva cuenta
    nueva_cuenta = Cuenta(
        nombre=cuenta.nombre,
        correo=cuenta.correo,
        contraseña=cuenta.contraseña,
        telefono=cuenta.telefono,
        nivel=cuenta.nivel,
        empresa=cuenta.empresa
    )
    db.add(nueva_cuenta)
    db.commit()
    db.refresh(nueva_cuenta)
    return nueva_cuenta


# Ruta para obtener todas las cuentas con paginación
@router.get("/", response_model=PaginatedCuentaResponse)
def obtener_cuentas(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    # Obtenemos las cuentas con paginación
    total_registros = db.query(Cuenta).count()
    cuentas = db.query(Cuenta).offset(skip).limit(limit).all()

    total_paginas = (total_registros + limit - 1) // limit  # Calculamos el total de páginas
    return PaginatedCuentaResponse(
        total_registros=total_registros,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=cuentas
    )


# Ruta para obtener una cuenta por su id
@router.get("/{cuenta_id}", response_model=CuentaResponse)
def obtener_cuenta(cuenta_id: int, db: Session = Depends(get_db)):
    cuenta = db.query(Cuenta).filter(Cuenta.id == cuenta_id).first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")
    return cuenta


# Ruta para actualizar una cuenta
@router.put("/{cuenta_id}", response_model=CuentaResponse)
def actualizar_cuenta(cuenta_id: int, cuenta: CuentaCreate, db: Session = Depends(get_db)):
    cuenta_existente = db.query(Cuenta).filter(Cuenta.id == cuenta_id).first()
    if not cuenta_existente:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

    # Actualizamos los valores de la cuenta
    cuenta_existente.nombre = cuenta.nombre
    cuenta_existente.correo = cuenta.correo
    cuenta_existente.contraseña = cuenta.contraseña
    cuenta_existente.telefono = cuenta.telefono
    cuenta_existente.nivel = cuenta.nivel
    cuenta_existente.empresa = cuenta.empresa
    db.commit()
    db.refresh(cuenta_existente)
    return cuenta_existente


# Ruta para eliminar una cuenta
@router.delete("/{cuenta_id}", response_model=CuentaResponse)
def eliminar_cuenta(cuenta_id: int, db: Session = Depends(get_db)):
    cuenta = db.query(Cuenta).filter(Cuenta.id == cuenta_id).first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

    db.delete(cuenta)
    db.commit()
    return cuenta
