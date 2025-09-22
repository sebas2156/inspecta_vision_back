from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models.productosector import ProductoSector
from servicio_general.schemas.productosector_schema import ProductoSectorCreate, ProductoSectorResponse
from shared.schemas.paginacion import PaginatedResponse
from confluent_kafka import Producer
import json
import threading
from sqlalchemy import and_

# Configuración de Kafka
KAFKA_CONFIG = {
    'bootstrap.servers': 'localhost:9092',
    'client.id': 'servicio-productosector'
}

# Crear productor Kafka
kafka_producer = Producer(KAFKA_CONFIG)


# Función para emitir eventos en segundo plano
def emitir_evento_kafka_async(evento):
    def delivery_report(err, msg):
        if err is not None:
            print(f'Error al entregar mensaje: {err}')
        else:
            print(f'Mensaje entregado a {msg.topic()} [{msg.partition()}]')

    try:
        evento_str = json.dumps(evento)
        kafka_producer.produce(
            topic='notificaciones',
            value=evento_str,
            callback=delivery_report
        )
        kafka_producer.flush()
    except Exception as e:
        print(f"Error al emitir evento Kafka: {e}")


router = APIRouter()


# Ruta para crear una nueva relación producto-sector
@router.post("/", response_model=ProductoSectorResponse)
def crear_productosector(productosector: ProductoSectorCreate, db: Session = Depends(get_db)):
    # Verificamos si ya existe usando la clave compuesta
    existing = db.query(ProductoSector).filter(
        and_(
            ProductoSector.producto_codigo == productosector.producto_codigo,
            ProductoSector.sector_id == productosector.sector_id,
            ProductoSector.empresa_id == productosector.empresa_id
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="La relación producto-sector ya existe para esta combinación de producto, sector y empresa."
        )

    # Creamos la nueva relación
    nueva_productosector = ProductoSector(**productosector.dict())
    db.add(nueva_productosector)
    db.commit()
    db.refresh(nueva_productosector)

    # Emitir evento de creación (solo datos relevantes para detección)
    evento = {
        "tipo": "producto_sector",
        "accion": "creado",
        "sector_id": nueva_productosector.sector_id,
        "producto_codigo": nueva_productosector.producto_codigo,
        "permitido": nueva_productosector.permitido
    }

    # Emitir en segundo plano
    threading.Thread(target=emitir_evento_kafka_async, args=(evento,)).start()

    return nueva_productosector


# Ruta para obtener todas las relaciones producto-sector con paginación
@router.get("/", response_model=PaginatedResponse[ProductoSectorResponse])
def obtener_productosector(
    empresa_id: int,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(ProductoSector).filter(ProductoSector.empresa_id == empresa_id)

    total_registros = query.count()
    productosector = query.offset(skip).limit(limit).all()

    total_paginas = (total_registros + limit - 1) // limit
    return PaginatedResponse(
        total_registros=total_registros,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=productosector
    )


# Ruta para actualizar una relación producto-sector
@router.put("/", response_model=ProductoSectorResponse)
def actualizar_productosector(
        producto_codigo: str,
        sector_id: int,
        empresa_id: int,
        productosector: ProductoSectorCreate,
        db: Session = Depends(get_db)
):
    # Buscar por clave compuesta
    productosector_existente = db.query(ProductoSector).filter(
        and_(
            ProductoSector.producto_codigo == producto_codigo,
            ProductoSector.sector_id == sector_id,
            ProductoSector.empresa_id == empresa_id
        )
    ).first()

    if not productosector_existente:
        raise HTTPException(
            status_code=404,
            detail="Relación producto-sector no encontrada."
        )

    # Guardamos el estado anterior de "permitido" para posible uso
    permitido_anterior = productosector_existente.permitido

    # Actualizamos los campos (excepto la clave compuesta)
    for key, value in productosector.dict().items():
        if key not in ['producto_codigo', 'sector_id', 'empresa_id']:
            setattr(productosector_existente, key, value)

    db.commit()
    db.refresh(productosector_existente)

    # Solo emitir evento si cambió el estado de "permitido"
    if permitido_anterior != productosector_existente.permitido:
        evento = {
            "tipo": "producto_sector",
            "accion": "actualizado",
            "sector_id": productosector_existente.sector_id,
            "producto_codigo": productosector_existente.producto_codigo,
            "permitido": productosector_existente.permitido
        }
        threading.Thread(target=emitir_evento_kafka_async, args=(evento,)).start()

    return productosector_existente


# Ruta para eliminar una relación producto-sector
@router.delete("/")
def eliminar_productosector(
        producto_codigo: str,
        sector_id: int,
        empresa_id: int,
        db: Session = Depends(get_db)
):
    productosector = db.query(ProductoSector).filter(
        and_(
            ProductoSector.producto_codigo == producto_codigo,
            ProductoSector.sector_id == sector_id,
            ProductoSector.empresa_id == empresa_id
        )
    ).first()

    if not productosector:
        raise HTTPException(
            status_code=404,
            detail="Relación producto-sector no encontrada."
        )

    db.delete(productosector)
    db.commit()

    # Emitir evento de eliminación
    evento = {
        "tipo": "producto_sector",
        "accion": "eliminado",
        "sector_id": sector_id,
        "producto_codigo": producto_codigo
    }

    threading.Thread(target=emitir_evento_kafka_async, args=(evento,)).start()

    return {"mensaje": "Relación producto-sector eliminada exitosamente"}