from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models.servicios import Servicios
from servicio_general.schemas.servicios_schema import ServiciosCreate, ServiciosResponse
from shared.schemas.paginacion import PaginatedResponse

router = APIRouter()


@router.post("/", response_model=ServiciosResponse)
def crear_servicios(servicios: ServiciosCreate, db: Session = Depends(get_db)):
    existing = db.query(Servicios).filter(Servicios.nombre == servicios.nombre).first()
    if existing:
        raise HTTPException(status_code=400, detail="El servicios ya existe")

    nuevo_servicios = Servicios(**servicios.dict())
    db.add(nuevo_servicios)
    db.commit()
    db.refresh(nuevo_servicios)
    return nuevo_servicios


@router.get("/", response_model=PaginatedResponse[ServiciosResponse])
def obtener_servicioss(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    total = db.query(Servicios).count()
    servicioss = db.query(Servicios).offset(skip).limit(limit).all()
    total_paginas = (total + limit - 1) // limit

    return PaginatedResponse(
        total_registros=total,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=servicioss
    )


@router.get("/{servicios_id}", response_model=ServiciosResponse)
def obtener_servicios(servicios_id: int, db: Session = Depends(get_db)):
    servicios = db.query(Servicios).get(servicios_id)
    if not servicios:
        raise HTTPException(status_code=404, detail="Servicios no encontrado")
    return servicios


@router.put("/{servicios_id}", response_model=ServiciosResponse)
def actualizar_servicios(servicios_id: int, servicios: ServiciosCreate, db: Session = Depends(get_db)):
    # Usamos filter() para obtener el servicio
    servicio_existente = db.query(Servicios).filter(Servicios.id == servicios_id).first()
    if not servicio_existente:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    # Actualizamos los campos de manera dinámica
    for key, value in servicios.dict().items():
        setattr(servicio_existente, key, value)

    # Guardamos los cambios en la base de datos
    db.commit()
    db.refresh(servicio_existente)

    return servicio_existente


@router.delete("/{servicios_id}", response_model=ServiciosResponse)
def eliminar_servicios(servicios_id: int, db: Session = Depends(get_db)):
    servicios = db.query(Servicios).get(servicios_id)
    if not servicios:
        raise HTTPException(status_code=404, detail="Servicios no encontrado")

    db.delete(servicios)
    db.commit()
    return servicios