from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models.regiones import Regiones
from shared.models.camaras import Camaras
from shared.schemas.regiones_schema import RegionesCreate, RegionesResponse
from shared.schemas.paginacion import PaginatedResponse
from confluent_kafka import Producer
import json

router = APIRouter()

# Configuración compartida del productor Kafka
kafka_conf = {
    'bootstrap.servers': 'localhost:9092',
    'client.id': 'fastapi-regiones-producer'
}

kafka_producer = Producer(kafka_conf)


def publicar_evento_regiones(accion: str, region_data: dict, camara_id: int):
    evento = {
        "tipo": "region",
        "accion": accion,
        "id": region_data["id"],
        "camara_id": camara_id,
        "coordenadas": region_data["coordenadas"],
        "restricciones_epp": region_data["restricciones_equipamiento"],
        "sector_id": region_data["sector_id"]
    }

    kafka_producer.produce(
        topic='notificaciones',
        key=str(camara_id),
        value=json.dumps(evento))
    kafka_producer.flush() \
 \
    @ router.post("/", response_model=RegionesResponse)


def crear_regiones(regiones: RegionesCreate, db: Session = Depends(get_db)):
    # Verificar existencia de la cámara relacionada
    camara = db.query(Camaras).get(regiones.camara_id)
    if not camara:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")

    nueva_regiones = Regiones(**regiones.dict())
    db.add(nueva_regiones)
    db.commit()
    db.refresh(nueva_regiones)

    # Publicar evento
    publicar_evento_regiones(
        "agregado",
        {
            "id": nueva_regiones.id,
            "coordenadas": nueva_regiones.coordenadas,
            "restricciones_equipamiento": nueva_regiones.restricciones_equipamiento,
            "sector_id": nueva_regiones.sector_id
        },
        nueva_regiones.camara_id
    )

    return nueva_regiones


@router.put("/{regiones_id}", response_model=RegionesResponse)
def actualizar_regiones(regiones_id: int, regiones: RegionesCreate, db: Session = Depends(get_db)):
    existente = db.query(Regiones).get(regiones_id)
    if not existente:
        raise HTTPException(status_code=404, detail="Región no encontrada")

    # Guardar datos antiguos para el evento
    datos_originales = {
        "coordenadas": existente.coordenadas,
        "restricciones_equipamiento": existente.restricciones_equipamiento,
        "sector_id": existente.sector_id
    }

    # Actualizar campos
    for key, value in regiones.dict().items():
        setattr(existente, key, value)

    db.commit()
    db.refresh(existente)

    # Publicar evento solo si hay cambios relevantes
    if any([
        datos_originales["coordenadas"] != existente.coordenadas,
        datos_originales["restricciones_equipamiento"] != existente.restricciones_equipamiento,
        datos_originales["sector_id"] != existente.sector_id
    ]):
        publicar_evento_regiones(
            "modificado",
            {
                "id": existente.id,
                "coordenadas": existente.coordenadas,
                "restricciones_equipamiento": existente.restricciones_equipamiento,
                "sector_id": existente.sector_id
            },
            existente.camara_id
        )

    return existente


@router.delete("/{regiones_id}", response_model=RegionesResponse)
def eliminar_regiones(regiones_id: int, db: Session = Depends(get_db)):
    regiones = db.query(Regiones).get(regiones_id)
    if not regiones:
        raise HTTPException(status_code=404, detail="Región no encontrada")

    # Publicar evento antes de eliminar
    publicar_evento_regiones(
        "eliminado",
        {
            "id": regiones.id,
            "coordenadas": regiones.coordenadas,
            "restricciones_equipamiento": regiones.restricciones_equipamiento,
            "sector_id": regiones.sector_id
        },
        regiones.camara_id
    )

    db.delete(regiones)
    db.commit()
    return regiones