from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models.suscripciones import Suscripciones
from servicio_general.schemas.suscripciones_schema import SuscripcionesCreate, SuscripcionesResponse
from shared.schemas.paginacion import PaginatedResponse
from confluent_kafka import Producer
import json
from datetime import datetime

router = APIRouter()

# Configuración del productor Kafka
kafka_conf = {
    'bootstrap.servers': 'localhost:9092',
    'client.id': 'fastapi-suscripciones-producer'
}

kafka_producer = Producer(kafka_conf)


def publicar_evento_suscripcion(accion: str, suscripcion_data: dict):
    evento = {
        "tipo": "suscripcion",
        "accion": accion,
        "id": suscripcion_data["id"],
        "empresa_id": suscripcion_data["empresa_id"],
        "servicio_id": suscripcion_data["servicio_id"],
        "modelo_id": suscripcion_data["modelo_id"],
        "fecha_inicio": suscripcion_data["fecha_inicio"].isoformat() if suscripcion_data["fecha_inicio"] else None,
        "fecha_fin": suscripcion_data["fecha_fin"].isoformat() if suscripcion_data["fecha_fin"] else None,
        "timestamp": datetime.utcnow().isoformat()
    }

    kafka_producer.produce(
        topic='notificaciones',
        key=str(suscripcion_data["id"]),
        value=json.dumps(evento))
    kafka_producer.flush() \
 \
    @ router.post("/", response_model=SuscripcionesResponse)


def crear_suscripcion(suscripcion: SuscripcionesCreate, db: Session = Depends(get_db)):
    # Verificar si ya existe una suscripción activa para este servicio y empresa
    existente = db.query(Suscripciones).filter(
        Suscripciones.empresa_id == suscripcion.empresa_id,
        Suscripciones.servicio_id == suscripcion.servicio_id,
        Suscripciones.fecha_fin >= datetime.utcnow().date()
    ).first()

    if existente:
        raise HTTPException(
            status_code=400,
            detail="Ya existe una suscripción activa para este servicio y empresa"
        )

    nueva_suscripcion = Suscripciones(**suscripcion.dict())
    db.add(nueva_suscripcion)
    db.commit()
    db.refresh(nueva_suscripcion)

    # Publicar evento de creación
    publicar_evento_suscripcion(
        "agregado",
        {
            "id": nueva_suscripcion.id,
            "empresa_id": nueva_suscripcion.empresa_id,
            "servicio_id": nueva_suscripcion.servicio_id,
            "modelo_id": nueva_suscripcion.modelo_id,
            "fecha_inicio": nueva_suscripcion.fecha_inicio,
            "fecha_fin": nueva_suscripcion.fecha_fin
        }
    )

    return nueva_suscripcion


@router.put("/{suscripcion_id}", response_model=SuscripcionesResponse)
def actualizar_suscripcion(suscripcion_id: int, suscripcion: SuscripcionesCreate, db: Session = Depends(get_db)):
    suscripcion_existente = db.query(Suscripciones).filter(Suscripciones.id == suscripcion_id).first()
    if not suscripcion_existente:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada")

    # Guardar datos antiguos para comparación
    datos_originales = {
        "modelo_id": suscripcion_existente.modelo_id,
        "fecha_fin": suscripcion_existente.fecha_fin
    }

    # Actualizar campos
    for key, value in suscripcion.dict().items():
        setattr(suscripcion_existente, key, value)

    db.commit()
    db.refresh(suscripcion_existente)

    # Publicar evento si hay cambios relevantes
    if (datos_originales["modelo_id"] != suscripcion_existente.modelo_id or
            datos_originales["fecha_fin"] != suscripcion_existente.fecha_fin):
        publicar_evento_suscripcion(
            "modificado",
            {
                "id": suscripcion_existente.id,
                "empresa_id": suscripcion_existente.empresa_id,
                "servicio_id": suscripcion_existente.servicio_id,
                "modelo_id": suscripcion_existente.modelo_id,
                "fecha_inicio": suscripcion_existente.fecha_inicio,
                "fecha_fin": suscripcion_existente.fecha_fin
            }
        )

    return suscripcion_existente


@router.delete("/{suscripcion_id}", response_model=SuscripcionesResponse)
def eliminar_suscripcion(suscripcion_id: int, db: Session = Depends(get_db)):
    suscripcion_existente = db.query(Suscripciones).filter(Suscripciones.id == suscripcion_id).first()
    if not suscripcion_existente:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada")

    # Publicar evento antes de eliminar
    publicar_evento_suscripcion(
        "eliminado",
        {
            "id": suscripcion_existente.id,
            "empresa_id": suscripcion_existente.empresa_id,
            "servicio_id": suscripcion_existente.servicio_id,
            "modelo_id": suscripcion_existente.modelo_id,
            "fecha_inicio": suscripcion_existente.fecha_inicio,
            "fecha_fin": suscripcion_existente.fecha_fin
        }
    )

    db.delete(suscripcion_existente)
    db.commit()
    return suscripcion_existente