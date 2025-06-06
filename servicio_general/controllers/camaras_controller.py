from confluent_kafka import Producer
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models.camaras import Camaras
from shared.models.regiones import Regiones
from shared.models import *
from shared.schemas.camaras_schema import CamarasCreate, CamarasResponse
from shared.schemas.paginacion import PaginatedResponse
import json
from collections import defaultdict
import ast

router = APIRouter()

# Configuración del productor Kafka
kafka_conf = {
    'bootstrap.servers': 'localhost:9092',
    'client.id': 'fastapi-producer'
}

kafka_producer = Producer(kafka_conf)


def publicar_evento_kafka(accion: str, camara_data: dict):
    evento = {
        "tipo": "camara",
        "accion": accion,
        "id": camara_data["id"],
        "ip": camara_data["ip"],
        "regiones": []
    }

    # Obtener regiones relacionadas
    db = next(get_db())
    try:
        regiones = db.query(Regiones).filter(Regiones.camara_id == camara_data["id"]).all()
        for region in regiones:
            evento["regiones"].append({
                "coordenadas": json.loads(region.coordenadas),
                "restricciones_epp": json.loads(region.restricciones_equipamiento),
                "sector_id": region.sector_id
            })
    finally:
        db.close()

    kafka_producer.produce(
        topic='notificaciones',
        key=str(camara_data["id"]),
        value=json.dumps(evento)
    )
    kafka_producer.flush()


@router.post("/", response_model=CamarasResponse)
def crear_camara(camara: CamarasCreate, db: Session = Depends(get_db)):
    existente = db.query(Camaras).filter(Camaras.ip == camara.ip).first()
    if existente:
        raise HTTPException(status_code=400, detail="La cámara ya existe")

    nueva_camara = Camaras(**camara.dict())
    db.add(nueva_camara)
    db.commit()
    db.refresh(nueva_camara)

    # Publicar evento de creación
    publicar_evento_kafka("agregado", {
        "id": nueva_camara.id,
        "ip": nueva_camara.ip
    })

    return nueva_camara


@router.put("/{camara_id}", response_model=CamarasResponse)
def actualizar_camara(camara_id: int, camara: CamarasCreate, db: Session = Depends(get_db)):
    existente = db.query(Camaras).get(camara_id)
    if not existente:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")

    for key, value in camara.dict().items():
        setattr(existente, key, value)

    db.commit()
    db.refresh(existente)

    # Publicar evento de actualización
    publicar_evento_kafka("modificado", {
        "id": existente.id,
        "ip": existente.ip
    })

    return existente


@router.delete("/{camara_id}", response_model=CamarasResponse)
def eliminar_camara(camara_id: int, db: Session = Depends(get_db)):
    camara = db.query(Camaras).get(camara_id)
    if not camara:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")

    # Publicar evento antes de eliminar
    publicar_evento_kafka("eliminado", {
        "id": camara.id,
        "ip": camara.ip
    })

    db.delete(camara)
    db.commit()
    return camara

@router.get("/config",
          response_model=list,
          summary="Obtener configuración completa",
          description="Devuelve la estructura completa de modelos, cámaras y configuraciones",
          tags=["Configuración"])
def obtener_configuracion(db: Session = Depends(get_db)):
    try:
        resultados = (
            db.query(
                Camaras.id.label('camara_id'),
                Camaras.ip,
                ModelosIa.id.label('modelo_id'),
                ModelosIa.ruta_modelo,
                Regiones.coordenadas,
                ReglasEpp.restricciones_equipamiento,
                Regiones.sector_id
            )
            .join(Regiones, Camaras.id == Regiones.camara_id)
            .join(ReglasEpp, ReglasEpp.sector_id == Regiones.sector_id)
            .join(Suscripciones, Suscripciones.id == ReglasEpp.suscripcion_id)
            .join(ModelosIa, ModelosIa.id == Suscripciones.modelo_id)
            .all()
        )

        config = defaultdict(lambda: defaultdict(dict))

        for row in resultados:
            modelo_id = row.modelo_id
            cam_id = row.camara_id

            if cam_id not in config[modelo_id]:
                config[modelo_id][cam_id] = {
                    "ip": row.ip,
                    "polygons": [],
                    "restricciones": [],
                    "sector_ids": [],
                    "ruta_modelo": row.ruta_modelo
                }

            # Parsear polígonos
            try:
                polygon = ast.literal_eval(row.coordenadas) if isinstance(row.coordenadas, str) else []
                if isinstance(polygon, list) and len(polygon) >= 3:
                    config[modelo_id][cam_id]["polygons"].append(polygon)
            except Exception:
                pass

            # Parsear restricciones
            try:
                restricciones = ast.literal_eval(row.restricciones_equipamiento) if isinstance(row.restricciones_equipamiento, str) else []
                if isinstance(restricciones, list):
                    config[modelo_id][cam_id]["restricciones"].extend(restricciones)
            except Exception:
                pass

            # Agregar sector ID
            config[modelo_id][cam_id]["sector_ids"].append(row.sector_id)

        lista_final = []
        for modelo_id, camaras in config.items():
            dispositivos = []
            for cam_id, datos in camaras.items():
                dispositivos.append({
                    "cam_id": cam_id,
                    "ip": datos["ip"],
                    "polygons": datos["polygons"],
                    "restricciones": datos["restricciones"],
                    "sector_ids": datos["sector_ids"]
                })

            lista_final.append({
                "modelo_id": modelo_id,
                "ruta_modelo": datos["ruta_modelo"],
                "dispositivos": dispositivos
            })

        return lista_final

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo configuración: {str(e)}"
        )