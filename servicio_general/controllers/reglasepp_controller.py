from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models.reglasepp import ReglasEpp
from shared.models.suscripciones import Suscripciones
from shared.models.modelosia import ModelosIa
from servicio_general.schemas.modelosia_schema import ModelosIaResponse
from pydantic import BaseModel, validator
from typing import List, Union
from shared.schemas.paginacion import PaginatedResponse
from confluent_kafka import Producer
import json

router = APIRouter()

# Configuración del productor Kafka
kafka_conf = {
    'bootstrap.servers': 'localhost:9092',
    'client.id': 'fastapi-reglasepp-producer'
}

kafka_producer = Producer(kafka_conf)


# Nuevo esquema que acepta tanto listas como strings JSON
class ReglasEppCreate(BaseModel):
    sector_id: int
    suscripcion_id: int
    restricciones_equipamiento: Union[List[str], str]

    @validator('restricciones_equipamiento', pre=True)
    def parse_restricciones(cls, v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                # Eliminar comillas adicionales y espacios
                cleaned = v.strip().replace('"[', '[').replace(']"', ']')
                return json.loads(cleaned)
            except json.JSONDecodeError:
                # Si falla el parseo, devolver el string como lista de un elemento
                return [v]
        return v


class ReglasEppResponse(BaseModel):
    regla_id: int
    sector_id: int
    suscripcion_id: int
    restricciones_equipamiento: List[str]

    class Config:
        orm_mode = True


def publicar_evento_regla_epp(accion: str, regla_data: dict):
    evento = {
        "tipo": "regla_epp",
        "accion": accion,
        "regla_id": regla_data["regla_id"],
        "sector_id": regla_data["sector_id"],
        "restricciones": regla_data["restricciones"]
    }

    kafka_producer.produce(
        topic='notificaciones',
        key=str(regla_data["sector_id"]),
        value=json.dumps(evento).encode('utf-8'))
    kafka_producer.flush()


@router.post("/", response_model=ReglasEppResponse)
def crear_reglasepp(reglasepp: ReglasEppCreate, db: Session = Depends(get_db)):
    # Verificar si ya existe una regla para este sector y suscripción
    existente = db.query(ReglasEpp).filter(
        ReglasEpp.sector_id == reglasepp.sector_id,
        ReglasEpp.suscripcion_id == reglasepp.suscripcion_id
    ).first()

    if existente:
        raise HTTPException(
            status_code=400,
            detail="Ya existe una regla para este sector y suscripción"
        )

    # Convertir restricciones a JSON
    restricciones_json = json.dumps(reglasepp.restricciones_equipamiento)

    nueva_reglasepp = ReglasEpp(
        sector_id=reglasepp.sector_id,
        suscripcion_id=reglasepp.suscripcion_id,
        restricciones_equipamiento=restricciones_json
    )
    db.add(nueva_reglasepp)
    db.commit()
    db.refresh(nueva_reglasepp)

    # Publicar evento de creación
    publicar_evento_regla_epp(
        "agregado",
        {
            "regla_id": nueva_reglasepp.regla_id,
            "sector_id": nueva_reglasepp.sector_id,
            "restricciones": reglasepp.restricciones_equipamiento
        }
    )

    # Convertir para respuesta
    nueva_reglasepp.restricciones_equipamiento = reglasepp.restricciones_equipamiento
    return nueva_reglasepp


@router.put("/{reglasepp_id}", response_model=ReglasEppResponse)
def actualizar_reglasepp(reglasepp_id: int, reglasepp: ReglasEppCreate, db: Session = Depends(get_db)):
    regla_existente = db.query(ReglasEpp).filter(ReglasEpp.regla_id == reglasepp_id).first()
    if not regla_existente:
        raise HTTPException(status_code=404, detail="Regla EPP no encontrada")

    # Guardar datos antiguos para comparación
    restricciones_originales = json.loads(regla_existente.restricciones_equipamiento)

    # Convertir nuevas restricciones a JSON
    restricciones_json = json.dumps(reglasepp.restricciones_equipamiento)

    # Actualizar campos
    regla_existente.sector_id = reglasepp.sector_id
    regla_existente.suscripcion_id = reglasepp.suscripcion_id
    regla_existente.restricciones_equipamiento = restricciones_json

    db.commit()
    db.refresh(regla_existente)

    # Publicar evento de actualización
    publicar_evento_regla_epp(
        "modificado",
        {
            "regla_id": regla_existente.regla_id,
            "sector_id": regla_existente.sector_id,
            "restricciones": reglasepp.restricciones_equipamiento
        }
    )

    # Convertir para respuesta
    regla_existente.restricciones_equipamiento = reglasepp.restricciones_equipamiento
    return regla_existente


@router.delete("/{reglasepp_id}", response_model=ReglasEppResponse)
def eliminar_reglasepp(reglasepp_id: int, db: Session = Depends(get_db)):
    reglasepp = db.query(ReglasEpp).filter(ReglasEpp.regla_id == reglasepp_id).first()
    if not reglasepp:
        raise HTTPException(status_code=404, detail="Regla EPP no encontrada")

    # Obtener restricciones para el evento
    restricciones = json.loads(reglasepp.restricciones_equipamiento)

    # Publicar evento antes de eliminar
    publicar_evento_regla_epp(
        "eliminado",
        {
            "regla_id": reglasepp.regla_id,
            "sector_id": reglasepp.sector_id,
            "restricciones": restricciones
        }
    )

    db.delete(reglasepp)
    db.commit()

    # Convertir para respuesta
    reglasepp.restricciones_equipamiento = restricciones
    return reglasepp


@router.get("/{reglasepp_id}", response_model=ReglasEppResponse)
def obtener_regla_por_id(reglasepp_id: int, db: Session = Depends(get_db)):
    regla = db.query(ReglasEpp).filter(ReglasEpp.regla_id == reglasepp_id).first()
    if not regla:
        raise HTTPException(status_code=404, detail="Regla EPP no encontrada")

    # Convertir restricciones de JSON a lista
    regla.restricciones_equipamiento = json.loads(regla.restricciones_equipamiento)
    return regla


@router.get("/", response_model=PaginatedResponse[ReglasEppResponse])
def listar_reglas(
        db: Session = Depends(get_db),
        suscripcion_id: int = Query(None, description="Filtrar por ID de suscripción"),
        page: int = Query(1, ge=1, description="Número de página"),
        per_page: int = Query(10, ge=1, le=100, description="Elementos por página")
):
    query = db.query(ReglasEpp)

    # Aplicar filtros
    if suscripcion_id is not None:
        query = query.filter(ReglasEpp.suscripcion_id == suscripcion_id)

    # Calcular paginación
    total = query.count()
    offset = (page - 1) * per_page
    reglas = query.offset(offset).limit(per_page).all()
    total_paginas = (total + per_page - 1) // per_page  # Cálculo simple de total de páginas

    # Convertir restricciones de JSON a lista para cada regla
    for regla in reglas:
        regla.restricciones_equipamiento = json.loads(regla.restricciones_equipamiento)

    return {
        "total_registros": total,
        "por_pagina": per_page,
        "pagina_actual": page,
        "total_paginas": total_paginas,
        "data": reglas
    }


@router.get("/sector/{sector_id}", response_model=ReglasEppResponse)
def obtener_regla_por_sector(sector_id: int, db: Session = Depends(get_db)):
    regla = db.query(ReglasEpp).filter(ReglasEpp.sector_id == sector_id).first()
    if not regla:
        raise HTTPException(status_code=404, detail="No se encontró regla para este sector")

    # Convertir restricciones de JSON a lista
    regla.restricciones_equipamiento = json.loads(regla.restricciones_equipamiento)
    return regla

# Nueva ruta para obtener el modelo asociado a una regla EPP
@router.get("/{regla_id}/modelo", response_model=ModelosIaResponse)
def obtener_modelo_por_regla(
    regla_id: int,
    db: Session = Depends(get_db)
):
    # Obtener la regla EPP
    regla = db.query(ReglasEpp).filter(ReglasEpp.regla_id == regla_id).first()
    if not regla:
        raise HTTPException(status_code=404, detail="Regla EPP no encontrada")

    # Obtener la suscripción asociada
    suscripcion = db.query(Suscripciones).filter(Suscripciones.id == regla.suscripcion_id).first()
    if not suscripcion:
        raise HTTPException(status_code=404, detail="Suscripción asociada no encontrada")

    # Obtener el modelo de IA
    modelo = db.query(ModelosIa).filter(ModelosIa.id == suscripcion.modelo_id).first()
    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo de IA asociado no encontrado")

    # Convertir las clases de JSON a lista
    try:
        modelo.classes = json.loads(modelo.classes)
    except json.JSONDecodeError:
        modelo.classes = []

    return modelo