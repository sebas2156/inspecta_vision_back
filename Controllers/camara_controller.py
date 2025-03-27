from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db  # Asumiendo que tienes esta función para obtener la sesión de la DB
from Models.camara import Camara  # Tu modelo de Camara
from Schemas.camara_schema import CamaraCreate, CamaraResponse, PaginatedCamaraResponse  # Los esquemas de Pydantic

router = APIRouter()


# Ruta para crear una nueva cámara
@router.post("/", response_model=CamaraResponse)
def crear_camara(camara: CamaraCreate, db: Session = Depends(get_db)):
    # Verificamos si la cámara ya existe
    existing_camara = db.query(Camara).filter(Camara.ip == camara.ip).first()
    if existing_camara:
        raise HTTPException(status_code=400, detail="La cámara con esa IP ya existe.")

    # Creamos la nueva cámara
    nueva_camara = Camara(empresa=camara.empresa, ip=camara.ip, nombre=camara.nombre, funciones=camara.funciones)
    db.add(nueva_camara)
    db.commit()
    db.refresh(nueva_camara)
    return nueva_camara


# Ruta para obtener todas las cámaras con paginación
@router.get("/", response_model=PaginatedCamaraResponse)
def obtener_camaras(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    # Obtenemos las cámaras con paginación
    total_registros = db.query(Camara).count()
    camaras = db.query(Camara).offset(skip).limit(limit).all()

    total_paginas = (total_registros + limit - 1) // limit  # Calculamos el total de páginas
    return PaginatedCamaraResponse(
        total_registros=total_registros,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=camaras
    )


# Ruta para obtener una cámara por su id
@router.get("/{camara_id}", response_model=CamaraResponse)
def obtener_camara(camara_id: int, db: Session = Depends(get_db)):
    camara = db.query(Camara).filter(Camara.id == camara_id).first()
    if not camara:
        raise HTTPException(status_code=404, detail="Cámara no encontrada.")
    return camara


# Ruta para actualizar una cámara
@router.put("/{camara_id}", response_model=CamaraResponse)
def actualizar_camara(camara_id: int, camara: CamaraCreate, db: Session = Depends(get_db)):
    camara_existente = db.query(Camara).filter(Camara.id == camara_id).first()
    if not camara_existente:
        raise HTTPException(status_code=404, detail="Cámara no encontrada.")

    # Actualizamos los valores de la cámara
    camara_existente.empresa = camara.empresa
    camara_existente.ip = camara.ip
    camara_existente.nombre = camara.nombre
    camara_existente.funciones = camara.funciones
    db.commit()
    db.refresh(camara_existente)
    return camara_existente


# Ruta para eliminar una cámara
@router.delete("/{camara_id}", response_model=CamaraResponse)
def eliminar_camara(camara_id: int, db: Session = Depends(get_db)):
    camara = db.query(Camara).filter(Camara.id == camara_id).first()
    if not camara:
        raise HTTPException(status_code=404, detail="Cámara no encontrada.")

    db.delete(camara)
    db.commit()
    return camara
