from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models.logs import Logs
from servicio_general.schemas.logs_schema import LogsCreate, LogsResponse
from shared.schemas.paginacion import PaginatedResponse

router = APIRouter()

# Ruta para crear un nuevo log
@router.post("/", response_model=LogsResponse)
def crear_log(log: LogsCreate, db: Session = Depends(get_db)):
    nuevo_log = Logs(cuenta_id=log.cuenta_id, accion=log.accion, fecha=log.fecha)
    db.add(nuevo_log)
    db.commit()
    db.refresh(nuevo_log)
    return nuevo_log


# Ruta para obtener todos los logs con paginación
@router.get("/", response_model=PaginatedResponse[LogsResponse])
def obtener_logs(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    total_registros = db.query(Logs).count()
    logs = db.query(Logs).offset(skip).limit(limit).all()
    total_paginas = (total_registros + limit - 1) // limit
    return PaginatedResponse(
        total_registros=total_registros,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=logs
    )


# Ruta para obtener un log por su id
@router.get("/{log_id}", response_model=LogsResponse)
def obtener_log(log_id: int, db: Session = Depends(get_db)):
    log = db.query(Logs).filter(Logs.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log no encontrado.")
    return log