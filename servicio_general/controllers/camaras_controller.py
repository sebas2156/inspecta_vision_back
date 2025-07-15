from confluent_kafka import Producer
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, aliased
from shared.database import get_db
from shared.models.camaras import Camaras
from shared.models.regiones import Regiones
from shared.models import *
from shared.schemas.camaras_schema import CamarasCreate, CamarasResponse, CamaraConRegionesCreate
from shared.schemas.regiones_schema import RegionesCreate
from shared.schemas.paginacion import PaginatedResponse
import json
from collections import defaultdict
import ast
from typing import List
from sqlalchemy import select, and_, or_, func

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


@router.get("/{camara_id}/servicios", summary="Obtener servicios relacionados a una cámara")
def obtener_servicios_por_camara(camara_id: int, db: Session = Depends(get_db)):
    try:
        # 1. Obtener sectores relacionados a la cámara vía regiones
        sectores_subq = (
            select(Regiones.sector_id)
            .where(Regiones.camara_id == camara_id)
            .scalar_subquery()
        )

        # 2. Obtener servicios desde reglas_epp (vía suscripciones)
        servicios_desde_reglas = (
            db.query(Servicios.id, Servicios.nombre)
            .join(Suscripciones, Suscripciones.servicio_id == Servicios.id)
            .join(ReglasEpp, ReglasEpp.suscripcion_id == Suscripciones.id)
            .filter(ReglasEpp.sector_id.in_(sectores_subq))
            .distinct()
            .all()
        )

        # 3. Obtener servicios desde producto_sector (vía productos y suscripciones)
        productos_sector_subq = (
            select(ProductoSector.producto_codigo)
            .where(ProductoSector.sector_id.in_(sectores_subq))
            .scalar_subquery()
        )

        servicios_desde_productos = (
            db.query(Servicios.id, Servicios.nombre)
            .join(Suscripciones, Suscripciones.servicio_id == Servicios.id)
            .join(Productos, Productos.suscripcion_id == Suscripciones.id)
            .filter(Productos.codigo.in_(productos_sector_subq))
            .distinct()
            .all()
        )

        # Unificar servicios (id, nombre) sin repetir
        servicios_set = {(s.id, s.nombre) for s in servicios_desde_reglas}
        servicios_set.update({(s.id, s.nombre) for s in servicios_desde_productos})

        servicios = [{"id": sid, "nombre": nombre} for sid, nombre in servicios_set]

        return {"camara_id": camara_id, "servicios": servicios}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener servicios: {str(e)}")

@router.get("/empresas/{empresa_id}/camaras-modelos")
def obtener_camaras_y_modelos_por_empresa(empresa_id: int, db: Session = Depends(get_db)):
    """
    Devuelve todas las cámaras de una empresa con sus modelos IA asociados.
    La cámara puede estar relacionada tanto con ReglasEpp como con ProductoSector o con ambos.
    """
    try:
        # Creamos alias para las instancias de "suscripciones" (una por reglas_epp y otra por producto_sector)
        suscripciones_regla = aliased(Suscripciones)
        suscripciones_producto = aliased(Suscripciones)

        # Creamos alias para los modelos IA
        modelos_ia_regla = aliased(ModelosIa)
        modelos_ia_producto = aliased(ModelosIa)

        # Realizamos la consulta con las relaciones necesarias
        resultados = (
            db.query(
                Camaras.id.label('camara_id'),
                Camaras.nombre.label('camara_nombre'),
                Camaras.ip,
                modelos_ia_regla.id.label('modelo_id'),
                modelos_ia_regla.nombre.label('modelo_nombre'),
                modelos_ia_regla.ruta_modelo,
                modelos_ia_producto.id.label('modelo_id_producto'),
                modelos_ia_producto.nombre.label('modelo_nombre_producto'),
                modelos_ia_producto.ruta_modelo.label('ruta_modelo_producto')
            )
            .join(Regiones, Camaras.id == Regiones.camara_id)
            .join(Sectores, Sectores.id == Regiones.sector_id)
            .outerjoin(ReglasEpp, ReglasEpp.sector_id == Sectores.id)  # Relación con reglas_epp
            .outerjoin(suscripciones_regla, suscripciones_regla.id == ReglasEpp.suscripcion_id)  # Relación con suscripciones de reglas_epp
            .outerjoin(modelos_ia_regla, modelos_ia_regla.id == suscripciones_regla.modelo_id)  # Relación con modelos IA de suscripciones de reglas_epp
            .outerjoin(ProductoSector, ProductoSector.sector_id == Sectores.id)  # Relación con producto_sector
            .outerjoin(Productos, Productos.codigo == ProductoSector.producto_codigo)  # Relación con productos
            .outerjoin(suscripciones_producto, suscripciones_producto.id == Productos.suscripcion_id)  # Relación con suscripciones de productos
            .outerjoin(modelos_ia_producto, modelos_ia_producto.id == suscripciones_producto.modelo_id)  # Relación con modelos IA de suscripciones de productos
            .filter(Sectores.empresa_id == empresa_id)
            .all()
        )

        camaras_dict = {}
        for row in resultados:
            cam_id = row.camara_id
            if cam_id not in camaras_dict:
                camaras_dict[cam_id] = {
                    "id": cam_id,
                    "nombre": row.camara_nombre,
                    "ip": row.ip,
                    "modelos": []
                }

            # Añadimos los modelos de "reglas_epp"
            if row.modelo_id:  # Solo agregar si el modelo está presente
                camaras_dict[cam_id]["modelos"].append({
                    "modelo_id": row.modelo_id,
                    "nombre": row.modelo_nombre,
                    "ruta_modelo": row.ruta_modelo
                })

            # Añadimos los modelos de "producto_sector"
            if row.modelo_id_producto:  # Solo agregar si el modelo de producto_sector está presente
                camaras_dict[cam_id]["modelos"].append({
                    "modelo_id": row.modelo_id_producto,
                    "nombre": row.modelo_nombre_producto,
                    "ruta_modelo": row.ruta_modelo_producto
                })

        return list(camaras_dict.values())

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")



@router.get("/", response_model=List[CamarasResponse])
def obtener_camaras(db: Session = Depends(get_db)):
    """
    Obtener todas las cámaras registradas.
    """
    camaras = db.query(Camaras).all()
    return camaras


@router.get("/{camara_id}", response_model=CamarasResponse)
def obtener_camara(camara_id: int, db: Session = Depends(get_db)):
    camara = db.query(Camaras).get(camara_id)
    if not camara:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")
    return camara
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

@router.get("/config/config",
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

@router.get(
    "/{camara_id}/servicio/{servicio_id}/regiones",
    summary="Obtener regiones de una cámara según servicio",
    description="Devuelve las regiones asociadas a la cámara filtradas por el servicio en cuyo contexto se está la pestaña."
)
def obtener_regiones_por_camara_y_servicio(
    camara_id: int,
    servicio_id: int,
    db: Session = Depends(get_db)
):
    try:
        # 1) IDs de suscripciones del servicio
        suscripciones_ids = [
            s.id
            for s in db.query(Suscripciones.id)
                     .filter(Suscripciones.servicio_id == servicio_id)
                     .all()
        ]

        # 2) Sectores por reglas EPP
        sectores_reglas = [
            r.sector_id
            for r in db.query(ReglasEpp.sector_id)
                     .filter(ReglasEpp.suscripcion_id.in_(suscripciones_ids))
                     .all()
        ]

        # 3) Sectores por productos (producto_sector → productos)
        sectores_productos = [
            ps.sector_id
            for ps in db.query(ProductoSector.sector_id)
                       .join(Productos,
                             and_(
                                 ProductoSector.producto_codigo == Productos.codigo,
                                 ProductoSector.empresa_id == Productos.empresa_id
                             ))
                       .filter(Productos.suscripcion_id.in_(suscripciones_ids))
                       .all()
        ]

        # 4) Unión de todos los sector_id
        sectores = set(sectores_reglas) | set(sectores_productos)
        if not sectores:
            return {"camara_id": camara_id, "servicio_id": servicio_id, "regiones": []}

        # 5) Consultar regiones filtrando por cámara y sectores
        regiones = (
            db.query(Regiones)
              .filter(
                  Regiones.camara_id == camara_id,
                  Regiones.sector_id.in_(sectores)
              )
              .all()
        )

        # 6) Formatear la respuesta con ast.literal_eval para coordenadas
        resultado = []
        for reg in regiones:
            # Parsear coordenadas de forma segura
            try:
                coords = ast.literal_eval(reg.coordenadas)
            except Exception:
                coords = []

            resultado.append({
                "id": reg.id,
                "coordenadas": coords,
                "color": reg.color,
                "sector_id": reg.sector_id
            })

        return {"camara_id": camara_id, "servicio_id": servicio_id, "regiones": resultado}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener regiones para cámara {camara_id} y servicio {servicio_id}: {e}"
        )


@router.post("/con-regiones", response_model=CamarasResponse)
def crear_camara_con_regiones(
        camara_data: CamaraConRegionesCreate,
        db: Session = Depends(get_db)
):
    # Crear la cámara
    nueva_camara = Camaras(
        empresa_id=camara_data.empresa_id,
        nombre=camara_data.nombre,
        ip=camara_data.ip,
        ubicacion=camara_data.ubicacion,
    )
    db.add(nueva_camara)
    db.flush()

    # Crear las regiones asociadas
    for region_data in camara_data.regiones:
        nueva_region = Regiones(
            camara_id=nueva_camara.id,
            sector_id=region_data.sector_id,
            coordenadas=region_data.coordenadas,
            color=region_data.color,
        )
        db.add(nueva_region)

    try:
        db.commit()
        db.refresh(nueva_camara)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar: {str(e)}")

    # Evento para la cámara
    evento_camara = {
        "tipo": "camara",
        "accion": "agregado",
        "id": nueva_camara.id,
        "empresa_id": nueva_camara.empresa_id,
        "ip": nueva_camara.ip,
    }

    # Publicar evento de cámara primero
    kafka_producer.produce(
        topic='notificaciones',
        key=str(nueva_camara.id),
        value=json.dumps(evento_camara)
    )

    # Eventos para cada región
    for region in nueva_camara.regiones:
        evento_region = {
            "tipo": "region",
            "accion": "agregado",
            "id": region.id,
            "camara_id": region.camara_id,
            "coordenadas": region.coordenadas,
            "sector_id": region.sector_id,
        }

        kafka_producer.produce(
            topic='notificaciones',
            key=str(region.camara_id),
            value=json.dumps(evento_region)
        )

    kafka_producer.flush()

    return nueva_camara