from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models.reglasepp import ReglasEpp
from servicio_general.schemas.reglasepp_schema import ReglasEppCreate, ReglasEppResponse
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


def publicar_evento_regla_epp(accion: str, regla_data: dict):
    evento = {
        "tipo": "regla_epp",
        "accion": accion,
        "regla_id": regla_data["id"],
        "sector_id": regla_data["sector_id"],
        "suscripcion_id": regla_data["suscripcion_id"],
        "restricciones": json.loads(regla_data["restricciones_equipamiento"])
    }

    kafka_producer.produce(
        topic='notificaciones',
        key=str(regla_data["sector_id"]),  # Usamos sector_id como clave
        value=json.dumps(evento))
    kafka_producer.flush() \
 \
    @ router.post("/", response_model=ReglasEppResponse)


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

    nueva_reglasepp = ReglasEpp(**reglasepp.dict())
    db.add(nueva_reglasepp)
    db.commit()
    db.refresh(nueva_reglasepp)

    # Publicar evento de creación
    publicar_evento_regla_epp(
        "agregado",
        {
            "id": nueva_reglasepp.id,
            "sector_id": nueva_reglasepp.sector_id,
            "suscripcion_id": nueva_reglasepp.suscripcion_id,
            "restricciones_equipamiento": nueva_reglasepp.restricciones_equipamiento
        }
    )

    return nueva_reglasepp


@router.put("/{reglasepp_id}", response_model=ReglasEppResponse)
def actualizar_reglasepp(reglasepp_id: int, reglasepp: ReglasEppCreate, db: Session = Depends(get_db)):
    regla_existente = db.query(ReglasEpp).filter(ReglasEpp.id == reglasepp_id).first()
    if not regla_existente:
        raise HTTPException(status_code=404, detail="Regla EPP no encontrada")

    # Guardar datos antiguos para comparación
    restricciones_originales = regla_existente.restricciones_equipamiento

    # Actualizar campos
    for key, value in reglasepp.dict().items():
        setattr(regla_existente, key, value)

    db.commit()
    db.refresh(regla_existente)

    # Publicar evento solo si las restricciones cambiaron
    if restricciones_originales != regla_existente.restricciones_equipamiento:
        publicar_evento_regla_epp(
            "modificado",
            {
                "id": regla_existente.id,
                "sector_id": regla_existente.sector_id,
                "suscripcion_id": regla_existente.suscripcion_id,
                "restricciones_equipamiento": regla_existente.restricciones_equipamiento
            }
        )

    return regla_existente


@router.delete("/{reglasepp_id}", response_model=ReglasEppResponse)
def eliminar_reglasepp(reglasepp_id: int, db: Session = Depends(get_db)):
    reglasepp = db.query(ReglasEpp).filter(ReglasEpp.id == reglasepp_id).first()
    if not reglasepp:
        raise HTTPException(status_code=404, detail="Regla EPP no encontrada")

    # Publicar evento antes de eliminar
    publicar_evento_regla_epp(
        "eliminado",
        {
            "id": reglasepp.id,
            "sector_id": reglasepp.sector_id,
            "suscripcion_id": reglasepp.suscripcion_id,
            "restricciones_equipamiento": reglasepp.restricciones_equipamiento
        }
    )

    db.delete(reglasepp)
    db.commit()
    return reglasepp