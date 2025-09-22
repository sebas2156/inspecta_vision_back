from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from shared.database import get_db  # Asumiendo que tienes esta función para obtener la sesión de la DB
from shared.models.modelosia import ModelosIa  # Tu modelo de ModelosIa
from servicio_general.schemas.modelosia_schema import ModelosIaCreate, ModelosIaResponse
from shared.schemas.paginacion import PaginatedResponse  # Los esquemas de Pydantic

from ultralytics import YOLO
import json

router = APIRouter()


# Ruta para crear un nuevo modelosia
@router.post("/", response_model=ModelosIaResponse)
def crear_modelosia(modelosia: ModelosIaCreate, db: Session = Depends(get_db)):
    # Creamos el nuevo modelosia
    nuevo_modelosia = ModelosIa(**modelosia.dict())
    db.add(nuevo_modelosia)
    db.commit()
    db.refresh(nuevo_modelosia)
    return nuevo_modelosia


# Ruta para obtener todos los modelosias con paginación
@router.get("/", response_model=PaginatedResponse[ModelosIaResponse])
def obtener_modelosias(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    # Obtenemos los modelosias con paginación
    total_registros = db.query(ModelosIa).count()
    modelosias = db.query(ModelosIa).offset(skip).limit(limit).all()

    total_paginas = (total_registros + limit - 1) // limit  # Calculamos el total de páginas
    return PaginatedResponse(
        total_registros=total_registros,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=modelosias
    )


# Ruta para obtener un modelosia por su código
@router.get("/{modelosia_id}", response_model=ModelosIaResponse)
def obtener_modelosia(modelosia_id: str, db: Session = Depends(get_db)):
    modelosia = db.query(ModelosIa).filter(ModelosIa.id == modelosia_id).first()

    if not modelosia:
        raise HTTPException(status_code=404, detail="ModelosIa no encontrado.")

    # Si no hay clases guardadas, las extraemos del modelo
    if not modelosia.classes:
        try:
            modelo_yolo = YOLO(modelosia.ruta_modelo)
            clases_lista = list(modelo_yolo.names.values())  # Solo nombres de clases
            modelosia.classes = json.dumps(clases_lista)  # Guardar como JSON de lista
            db.commit()
            db.refresh(modelosia)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al cargar el modelo: {str(e)}")

    # Parseamos antes de devolver
    clases_lista = json.loads(modelosia.classes)

    return {
        "id": modelosia.id,
        "nombre": modelosia.nombre,
        "ruta_modelo": modelosia.ruta_modelo,
        "classes": clases_lista
    }

# Ruta para actualizar un modelosia
@router.put("/{modelosia_id}", response_model=ModelosIaResponse)
def actualizar_modelosia(modelosia_id: str, modelosia: ModelosIaCreate, db: Session = Depends(get_db)):
    # Verificamos si el modelo IA existe
    modelosia_existente = db.query(ModelosIa).filter(ModelosIa.id == modelosia_id).first()
    if not modelosia_existente:
        raise HTTPException(status_code=404, detail="ModelosIa no encontrado.")

    # Actualizamos los campos del modelo IA de manera más eficiente
    for key, value in modelosia.dict().items():
        setattr(modelosia_existente, key, value)

    # Guardamos los cambios en la base de datos
    db.commit()
    db.refresh(modelosia_existente)

    return modelosia_existente


# Ruta para eliminar un modelosia
@router.delete("/{modelosia_id}", response_model=ModelosIaResponse)
def eliminar_modelosia(modelosia_id: str, db: Session = Depends(get_db)):
    modelosia = db.query(ModelosIa).filter(ModelosIa.id == modelosia_id).first()
    if not modelosia:
        raise HTTPException(status_code=404, detail="ModelosIa no encontrado.")

    db.delete(modelosia)
    db.commit()
    return modelosia