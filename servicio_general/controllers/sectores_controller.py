from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import exists, select
from shared.database import get_db
from shared.models.sectores import Sectores
from shared.models.productosector import ProductoSector
from shared.models.reglasepp import ReglasEpp
from servicio_general.schemas.sectores_schema import SectoresCreate, SectoresResponse
from shared.schemas.paginacion import PaginatedResponse

router = APIRouter()


@router.post("/", response_model=SectoresResponse)
def crear_relacion(ps: SectoresCreate, db: Session = Depends(get_db)):
    nuevo_sector = Sectores(**ps.dict())
    db.add(nuevo_sector)
    db.commit()
    db.refresh(nuevo_sector)
    return nuevo_sector


@router.get("/", response_model=PaginatedResponse[SectoresResponse])
def obtener_relaciones(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    total = db.query(Sectores).count()
    relaciones = db.query(Sectores).offset(skip).limit(limit).all()
    total_paginas = (total + limit - 1) // limit

    return PaginatedResponse(
        total_registros=total,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=relaciones
    )


@router.get("/{sectores_id}", response_model=SectoresResponse)
def obtener_relacion(sectores_id: int, db: Session = Depends(get_db)):
    rel = db.query(Sectores).filter(Sectores.id == sectores_id).first()  # Usamos .filter() para búsqueda por ID
    if not rel:
        raise HTTPException(status_code=404, detail="no encontrada")
    return rel


@router.put("/{sectores_id}", response_model=SectoresResponse)
def actualizar_relacion(sectores_id: int, sectores: SectoresCreate, db: Session = Depends(get_db)):
    rel = db.query(Sectores).filter(Sectores.id == sectores_id).first()  # Usamos .filter() para búsqueda por ID
    if not rel:
        raise HTTPException(status_code=404, detail="no encontrada")

    # Actualizamos los campos de la relación
    for key, value in sectores.dict().items():
        setattr(rel, key, value)

    db.commit()
    db.refresh(rel)
    return rel


@router.delete("/{sectores_id}", response_model=SectoresResponse)
def eliminar_relacion(sectores_id: int, db: Session = Depends(get_db)):
    rel = db.query(Sectores).filter(Sectores.id == sectores_id).first()  # Usamos .filter() para búsqueda por ID
    if not rel:
        raise HTTPException(status_code=404, detail="no encontrada")

    db.delete(rel)
    db.commit()
    return rel


# Versión corregida usando join explícito
@router.get("/con-productos/", response_model=PaginatedResponse[SectoresResponse])
def obtener_sectores_con_productos(
        skip: int = 0,
        limit: int = 10,
        db: Session = Depends(get_db)
):
    # Consulta con JOIN explícito para asegurar relación
    query = db.query(Sectores).join(
        ProductoSector,
        ProductoSector.sector_id == Sectores.id
    ).distinct(Sectores.id)

    total = query.count()
    sectores = query.offset(skip).limit(limit).all()
    total_paginas = (total + limit - 1) // limit

    return PaginatedResponse(
        total_registros=total,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=sectores
    )


# Versión alternativa usando subquery EXISTS (más eficiente)
@router.get("/con-reglas-epp/", response_model=PaginatedResponse[SectoresResponse])
def obtener_sectores_con_reglas_epp(
        skip: int = 0,
        limit: int = 10,
        db: Session = Depends(get_db)
):
    # Subquery para verificar existencia en reglas_epp
    has_rule = select(1).where(ReglasEpp.sector_id == Sectores.id).exists()
    query = db.query(Sectores).filter(has_rule)

    total = query.count()
    sectores = query.offset(skip).limit(limit).all()
    total_paginas = (total + limit - 1) // limit

    return PaginatedResponse(
        total_registros=total,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=sectores
    )