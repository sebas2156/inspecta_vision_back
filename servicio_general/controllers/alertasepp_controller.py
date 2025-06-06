from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from shared.database import get_db  # Asumiendo que tienes esta función para obtener la sesión de la DB
from shared.models.alertasepp import AlertasEpp  # Tu modelo de AlertasEpp
from servicio_general.schemas.alertasepp_schema import AlertasEppCreate, AlertasEppResponse
from shared.schemas.paginacion import PaginatedResponse  # Los esquemas de Pydantic

router = APIRouter()


# Ruta para crear una nueva alertasepp
@router.post("/", response_model=AlertasEppResponse)
def crear_alertasepp(alertasepp: AlertasEppCreate, db: Session = Depends(get_db)):
    # Verificamos si la alertasepp con el mismo correo ya existe
    existing_alertasepp = db.query(AlertasEpp).filter(AlertasEpp.correo == alertasepp.correo).first()
    if existing_alertasepp:
        raise HTTPException(status_code=400, detail="La alertasepp ya existe.")

    # Creamos la nueva alertasepp
    nueva_alertasepp = AlertasEpp(**alertasepp.dict())
    db.add(nueva_alertasepp)
    db.commit()
    db.refresh(nueva_alertasepp)
    return nueva_alertasepp


# Ruta para obtener todas las alertasepp con paginación
@router.get("/", response_model=PaginatedResponse[AlertasEppResponse])
def obtener_alertasepp(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    # Obtenemos las alertasepp con paginación
    total_registros = db.query(AlertasEpp).count()
    alertasepp = db.query(AlertasEpp).offset(skip).limit(limit).all()

    total_paginas = (total_registros + limit - 1) // limit  # Calculamos el total de páginas
    return PaginatedResponse(
        total_registros=total_registros,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=alertasepp
    )


# Ruta para obtener una alertasepp por su id
@router.get("/{alertasepp_id}", response_model=AlertasEppResponse)
def obtener_alertasepp(alertasepp_id: int, db: Session = Depends(get_db)):
    alertasepp = db.query(AlertasEpp).filter(AlertasEpp.id == alertasepp_id).first()
    if not alertasepp:
        raise HTTPException(status_code=404, detail="AlertasEpp no encontrada.")
    return alertasepp


# Ruta para actualizar una alertasepp
@router.put("/{alertasepp_id}", response_model=AlertasEppResponse, tags=["AlertasEpp"])
def actualizar_alertasepp(alertasepp_id: int, alertasepp: AlertasEppCreate, db: Session = Depends(get_db)):
    # Verificamos si la cuenta existe
    alertasepp_existente = db.query(AlertasEpp).filter(AlertasEpp.id == alertasepp_id).first()
    if not alertasepp_existente:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

    # Actualizamos los campos de la cuenta de manera más eficiente
    for key, value in alertasepp.dict().items():
        setattr(alertasepp_existente, key, value)

    # Guardamos los cambios en la base de datos
    db.commit()
    db.refresh(alertasepp_existente)

    return alertasepp_existente


# Ruta para eliminar una alertasepp
@router.delete("/{alertasepp_id}", response_model=AlertasEppResponse)
def eliminar_alertasepp(alertasepp_id: int, db: Session = Depends(get_db)):
    alertasepp = db.query(AlertasEpp).filter(AlertasEpp.id == alertasepp_id).first()
    if not alertasepp:
        raise HTTPException(status_code=404, detail="AlertasEpp no encontrada.")

    db.delete(alertasepp)
    db.commit()
    return alertasepp