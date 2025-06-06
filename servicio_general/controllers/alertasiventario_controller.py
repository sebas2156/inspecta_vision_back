from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from shared.database import get_db  # Asumiendo que tienes esta función para obtener la sesión de la DB
from shared.models.alertasinventario import AlertasInventario  # Tu modelo de AlertasInventario
from servicio_general.schemas.alertasinventario_schema import AlertasInventarioCreate, AlertasInventarioResponse
from shared.schemas.paginacion import PaginatedResponse  # Los esquemas de Pydantic

router = APIRouter()


# Ruta para crear una nueva alertasinventario
@router.post("/", response_model=AlertasInventarioResponse)
def crear_alertasinventario(alertasinventario: AlertasInventarioCreate, db: Session = Depends(get_db)):
    # Verificamos si la alertasinventario con el mismo correo ya existe
    existing_alertasinventario = db.query(AlertasInventario).filter(AlertasInventario.correo == alertasinventario.correo).first()
    if existing_alertasinventario:
        raise HTTPException(status_code=400, detail="La alertasinventario ya existe.")

    # Creamos la nueva alertasinventario
    nueva_alertasinventario = AlertasInventario(**alertasinventario.dict())
    db.add(nueva_alertasinventario)
    db.commit()
    db.refresh(nueva_alertasinventario)
    return nueva_alertasinventario


# Ruta para obtener todas las alertasinventario con paginación
@router.get("/", response_model=PaginatedResponse[AlertasInventarioResponse])
def obtener_alertasinventario(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    # Obtenemos las alertasinventario con paginación
    total_registros = db.query(AlertasInventario).count()
    alertasinventario = db.query(AlertasInventario).offset(skip).limit(limit).all()

    total_paginas = (total_registros + limit - 1) // limit  # Calculamos el total de páginas
    return PaginatedResponse(
        total_registros=total_registros,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=alertasinventario
    )


# Ruta para obtener una alertasinventario por su id
@router.get("/{alertasinventario_id}", response_model=AlertasInventarioResponse)
def obtener_alertasinventario(alertasinventario_id: int, db: Session = Depends(get_db)):
    alertasinventario = db.query(AlertasInventario).filter(AlertasInventario.id == alertasinventario_id).first()
    if not alertasinventario:
        raise HTTPException(status_code=404, detail="AlertasInventario no encontrada.")
    return alertasinventario


# Ruta para actualizar una alertasinventario
@router.put("/{alertasinventario_id}", response_model=AlertasInventarioResponse, tags=["AlertasInventario"])
def actualizar_alertasinventario(alertasinventario_id: int, alertasinventario: AlertasInventarioCreate, db: Session = Depends(get_db)):
    # Verificamos si la cuenta existe
    alertasinventario_existente = db.query(AlertasInventario).filter(AlertasInventario.id == alertasinventario_id).first()
    if not alertasinventario_existente:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

    # Actualizamos los campos de la cuenta de manera más eficiente
    for key, value in alertasinventario.dict().items():
        setattr(alertasinventario_existente, key, value)

    # Guardamos los cambios en la base de datos
    db.commit()
    db.refresh(alertasinventario_existente)

    return alertasinventario_existente


# Ruta para eliminar una alertasinventario
@router.delete("/{alertasinventario_id}", response_model=AlertasInventarioResponse)
def eliminar_alertasinventario(alertasinventario_id: int, db: Session = Depends(get_db)):
    alertasinventario = db.query(AlertasInventario).filter(AlertasInventario.id == alertasinventario_id).first()
    if not alertasinventario:
        raise HTTPException(status_code=404, detail="AlertasInventario no encontrada.")

    db.delete(alertasinventario)
    db.commit()
    return alertasinventario