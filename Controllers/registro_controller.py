from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db  # Asumiendo que tienes esta función para obtener la sesión de la DB
from Models.registro import Registro  # Tu modelo de Registro
from Schemas.registro_schema import RegistroCreate, RegistroResponse, PaginatedRegistroResponse  # Los esquemas de Pydantic

router = APIRouter()


# Ruta para crear un nuevo registro
@router.post("/", response_model=RegistroResponse)
def crear_registro(registro: RegistroCreate, db: Session = Depends(get_db)):
    # Creamos el nuevo registro
    nuevo_registro = Registro(
        sector=registro.sector,
        producto=registro.producto,
        accion=registro.accion,
        fecha=registro.fecha  # Puede ser `datetime.now()` o similar si es necesario
    )
    db.add(nuevo_registro)
    db.commit()
    db.refresh(nuevo_registro)
    return nuevo_registro


# Ruta para obtener todos los registros con paginación
@router.get("/", response_model=PaginatedRegistroResponse)
def obtener_registros(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    # Obtenemos los registros con paginación
    total_registros = db.query(Registro).count()
    registros = db.query(Registro).offset(skip).limit(limit).all()

    total_paginas = (total_registros + limit - 1) // limit  # Calculamos el total de páginas
    return PaginatedRegistroResponse(
        total_registros=total_registros,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=registros
    )


# Ruta para obtener un registro por su id
@router.get("/{registro_id}", response_model=RegistroResponse)
def obtener_registro(registro_id: int, db: Session = Depends(get_db)):
    registro = db.query(Registro).filter(Registro.id == registro_id).first()
    if not registro:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    return registro


# Ruta para actualizar un registro
@router.put("/{registro_id}", response_model=RegistroResponse)
def actualizar_registro(registro_id: int, registro: RegistroCreate, db: Session = Depends(get_db)):
    registro_existente = db.query(Registro).filter(Registro.id == registro_id).first()
    if not registro_existente:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")

    # Actualizamos los valores del registro
    registro_existente.sector = registro.sector
    registro_existente.producto = registro.producto
    registro_existente.accion = registro.accion
    registro_existente.fecha = registro.fecha  # Si es necesario, actualizamos la fecha
    db.commit()
    db.refresh(registro_existente)
    return registro_existente


# Ruta para eliminar un registro
@router.delete("/{registro_id}", response_model=RegistroResponse)
def eliminar_registro(registro_id: int, db: Session = Depends(get_db)):
    registro = db.query(Registro).filter(Registro.id == registro_id).first()
    if not registro:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")

    db.delete(registro)
    db.commit()
    return registro
