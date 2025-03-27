from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db  # Asumiendo que tienes esta función para obtener la sesión de la DB
from Models.region import Region  # Tu modelo de Region
from Schemas.region_schema import RegionCreate, RegionResponse, PaginatedRegionResponse  # Los esquemas de Pydantic

router = APIRouter()


# Ruta para crear una nueva región
@router.post("/", response_model=RegionResponse)
def crear_region(region: RegionCreate, db: Session = Depends(get_db)):
    # Verificamos si la región ya existe por puntos (si aplica)
    existing_region = db.query(Region).filter(Region.puntos == region.puntos).first()
    if existing_region:
        raise HTTPException(status_code=400, detail="La región con esos puntos ya existe.")

    # Creamos la nueva región
    nueva_region = Region(
        puntos=region.puntos,
        color=region.color,
        sector=region.sector
    )
    db.add(nueva_region)
    db.commit()
    db.refresh(nueva_region)
    return nueva_region


# Ruta para obtener todas las regiones con paginación
@router.get("/", response_model=PaginatedRegionResponse)
def obtener_regiones(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    # Obtenemos las regiones con paginación
    total_registros = db.query(Region).count()
    regiones = db.query(Region).offset(skip).limit(limit).all()

    total_paginas = (total_registros + limit - 1) // limit  # Calculamos el total de páginas
    return PaginatedRegionResponse(
        total_registros=total_registros,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=regiones
    )


# Ruta para obtener una región por su id
@router.get("/{region_id}", response_model=RegionResponse)
def obtener_region(region_id: int, db: Session = Depends(get_db)):
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Región no encontrada.")
    return region


# Ruta para actualizar una región
@router.put("/{region_id}", response_model=RegionResponse)
def actualizar_region(region_id: int, region: RegionCreate, db: Session = Depends(get_db)):
    region_existente = db.query(Region).filter(Region.id == region_id).first()
    if not region_existente:
        raise HTTPException(status_code=404, detail="Región no encontrada.")

    # Actualizamos los valores de la región
    region_existente.puntos = region.puntos
    region_existente.color = region.color
    region_existente.sector = region.sector
    db.commit()
    db.refresh(region_existente)
    return region_existente


# Ruta para eliminar una región
@router.delete("/{region_id}", response_model=RegionResponse)
def eliminar_region(region_id: int, db: Session = Depends(get_db)):
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Región no encontrada.")

    db.delete(region)
    db.commit()
    return region
