from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db  # Asumiendo que tienes esta función para obtener la sesión de la DB
from Models.sector import Sector  # Tu modelo de Sector
from Schemas.sector_schema import SectorCreate, SectorResponse, PaginatedSectorResponse  # Los esquemas de Pydantic

router = APIRouter()


# Ruta para crear un nuevo sector
@router.post("/", response_model=SectorResponse)
def crear_sector(sector: SectorCreate, db: Session = Depends(get_db)):
    # Verificamos si el sector ya existe
    existing_sector = db.query(Sector).filter(Sector.producto == sector.producto).first()
    if existing_sector:
        raise HTTPException(status_code=400, detail="El sector ya existe.")

    # Creamos el nuevo sector
    nuevo_sector = Sector(producto=sector.producto, unidades=sector.unidades)
    db.add(nuevo_sector)
    db.commit()
    db.refresh(nuevo_sector)
    return nuevo_sector


# Ruta para obtener todos los sectores con paginación
@router.get("/", response_model=PaginatedSectorResponse)
def obtener_sectores(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    # Obtenemos los sectores con paginación
    total_registros = db.query(Sector).count()
    sectores = db.query(Sector).offset(skip).limit(limit).all()

    total_paginas = (total_registros + limit - 1) // limit  # Calculamos el total de páginas
    return PaginatedSectorResponse(
        total_registros=total_registros,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=sectores
    )


# Ruta para obtener un sector por su id
@router.get("/{sector_id}", response_model=SectorResponse)
def obtener_sector(sector_id: int, db: Session = Depends(get_db)):
    sector = db.query(Sector).filter(Sector.id == sector_id).first()
    if not sector:
        raise HTTPException(status_code=404, detail="Sector no encontrado.")
    return sector


# Ruta para actualizar un sector
@router.put("/{sector_id}", response_model=SectorResponse)
def actualizar_sector(sector_id: int, sector: SectorCreate, db: Session = Depends(get_db)):
    sector_existente = db.query(Sector).filter(Sector.id == sector_id).first()
    if not sector_existente:
        raise HTTPException(status_code=404, detail="Sector no encontrado.")

    # Actualizamos los valores del sector
    sector_existente.producto = sector.producto
    sector_existente.unidades = sector.unidades
    db.commit()
    db.refresh(sector_existente)
    return sector_existente


# Ruta para eliminar un sector
@router.delete("/{sector_id}", response_model=SectorResponse)
def eliminar_sector(sector_id: int, db: Session = Depends(get_db)):
    sector = db.query(Sector).filter(Sector.id == sector_id).first()
    if not sector:
        raise HTTPException(status_code=404, detail="Sector no encontrado.")

    db.delete(sector)
    db.commit()
    return sector
