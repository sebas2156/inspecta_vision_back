from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models.regiones import Regiones
from shared.models.camaras import Camaras
from shared.schemas.regiones_schema import RegionesCreate, RegionesResponse
from confluent_kafka import Producer
import json

router = APIRouter()

# Configuración del productor Kafka
kafka_conf = {'bootstrap.servers': 'localhost:9092', 'client.id': 'fastapi-regiones-producer'}
kafka_producer = Producer(kafka_conf)


def publicar_evento_regiones(accion: str, region_data: dict, camara_id: int):
    """Publica evento Kafka solo con datos de regiones"""
    evento = {
        "tipo": "region",
        "accion": accion,
        "id": region_data["id"],
        "camara_id": camara_id,
        "coordenadas": region_data["coordenadas"],
        "sector_id": region_data["sector_id"]
    }
    kafka_producer.produce(
        topic='notificaciones',
        key=str(camara_id),
        value=json.dumps(evento)
    )
    kafka_producer.flush()


@router.post("/", response_model=RegionesResponse)
def crear_regiones(regiones: RegionesCreate, db: Session = Depends(get_db)):
    """Crea una nueva región"""
    camara = db.query(Camaras).get(regiones.camara_id)
    if not camara:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")

    nueva_regiones = Regiones(
        camara_id=regiones.camara_id,
        sector_id=regiones.sector_id,
        coordenadas=regiones.coordenadas,
        color=regiones.color
    )

    db.add(nueva_regiones)
    db.commit()
    db.refresh(nueva_regiones)

    # Publicar evento
    publicar_evento_regiones(
        "agregado",
        {
            "id": nueva_regiones.id,
            "coordenadas": nueva_regiones.coordenadas,
            "sector_id": nueva_regiones.sector_id
        },
        nueva_regiones.camara_id
    )

    return nueva_regiones


@router.get("/", response_model=list[RegionesResponse])
def listar_regiones(db: Session = Depends(get_db)):
    """Lista todas las regiones"""
    return db.query(Regiones).all()


@router.get("/{regiones_id}", response_model=RegionesResponse)
def obtener_region(regiones_id: int, db: Session = Depends(get_db)):
    """Obtiene una región específica por ID"""
    region = db.query(Regiones).get(regiones_id)
    if not region:
        raise HTTPException(status_code=404, detail="Región no encontrada")
    return region


@router.put("/{regiones_id}", response_model=RegionesResponse)
def actualizar_regiones(regiones_id: int, regiones: RegionesCreate, db: Session = Depends(get_db)):
    """Actualiza una región existente"""
    existente = db.query(Regiones).get(regiones_id)
    if not existente:
        raise HTTPException(status_code=404, detail="Región no encontrada")

    # Guardar datos antiguos para comparación
    datos_originales = {
        "coordenadas": existente.coordenadas,
        "sector_id": existente.sector_id
    }

    # Actualizar solo campos permitidos
    existente.camara_id = regiones.camara_id
    existente.coordenadas = regiones.coordenadas
    existente.color = regiones.color

    # Solo actualizar el sector_id si el valor recibido es distinto de 0
    if regiones.sector_id != 0:
        existente.sector_id = regiones.sector_id

    db.commit()
    db.refresh(existente)

    # Publicar evento solo si hay cambios relevantes
    if (datos_originales["coordenadas"] != existente.coordenadas or
            datos_originales["sector_id"] != existente.sector_id):
        publicar_evento_regiones(
            "modificado",
            {
                "id": existente.id,
                "coordenadas": existente.coordenadas,
                "sector_id": existente.sector_id
            },
            existente.camara_id
        )

    return existente


@router.delete("/{regiones_id}", response_model=RegionesResponse)
def eliminar_regiones(regiones_id: int, db: Session = Depends(get_db)):
    """Elimina una región"""
    regiones = db.query(Regiones).get(regiones_id)
    if not regiones:
        raise HTTPException(status_code=404, detail="Región no encontrada")

    # Publicar evento antes de eliminar
    publicar_evento_regiones(
        "eliminado",
        {
            "id": regiones.id,
            "coordenadas": regiones.coordenadas,
            "sector_id": regiones.sector_id
        },
        regiones.camara_id
    )

    db.delete(regiones)
    db.commit()
    return regiones