from fastapi import FastAPI
from confluent_kafka import KafkaError
from fastapi.middleware.cors import CORSMiddleware
from servicio_general.controllers.camaras_controller import router as camara_router
from servicio_general.controllers.cuentas_controller import router as cuenta_router
from servicio_general.controllers.regiones_controller import router as region_router
from servicio_general.controllers.sectores_controller import router as sector_router
from servicio_general.controllers.empresas_controller import router as empresa_router
from servicio_general.controllers.servicios_controller import router as servicios_router
from servicio_general.controllers.logs_controller import router as logs_router
from servicio_general.controllers.suscripciones_controller import router as suscripciones_router
from servicio_general.controllers.modelosia_controller import router as modelosia_router
from servicio_general.controllers.reglasepp_controller import router as reglasepp_router
from servicio_general.controllers.alertasepp_controller import router as alertasepp_router
from servicio_general.controllers.productos_controller import router as productos_router
from servicio_general.controllers.alertasiventario_controller import router as alertasiventario_router
from servicio_general.controllers.registroinventario_controller import router as registroinventario_router
from servicio_general.controllers.productosector_controller import router as productosector_router

from shared.database import Base, engine
import threading
import json
from confluent_kafka import Consumer
import requests
import os
import logging
import time
from datetime import datetime, timedelta

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configurar CORS
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crea las tablas en la base de datos
Base.metadata.create_all(bind=engine)

# Incluir routers
app.include_router(camara_router, prefix="/api/camaras", tags=["Camaras"])
app.include_router(cuenta_router, prefix="/api/cuentas", tags=["Cuentas"])
app.include_router(region_router, prefix="/api/regiones", tags=["Regiones"])
app.include_router(sector_router, prefix="/api/sectores", tags=["Sectores"])
app.include_router(logs_router, prefix="/api/logs", tags=["Logs"])
app.include_router(suscripciones_router, prefix="/api/suscripciones", tags=["Suscripciones"])
app.include_router(empresa_router, prefix="/api/empresas", tags=["Empresas"])
app.include_router(servicios_router, prefix="/api/servicios", tags=["Servicios"])
app.include_router(modelosia_router, prefix="/api/modelosia", tags=["Modelosia"])
app.include_router(reglasepp_router, prefix="/api/reglasepp", tags=["Reglas EPP"])
app.include_router(alertasepp_router, prefix="/api/alertasepp", tags=["Alertas EPP"])
app.include_router(productos_router, prefix="/api/productos", tags=["Productos"])
app.include_router(alertasiventario_router, prefix="/api/alertasiventario", tags=["Alertas Iventario"])
app.include_router(registroinventario_router, prefix="/api/registroinventario", tags=["Registro Inventario"])
app.include_router(productosector_router, prefix="/api/productosector", tags=["Productos por Sector"])

# Configuración de Kafka
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'localhost:9092')
FASTAPI_BASE_URL = os.getenv('FASTAPI_BASE_URL', 'http://localhost:8000')
MAX_RETRIES = 3
RETRY_DELAY = 2  # segundos

# Mapeo de topics a endpoints
TOPIC_ENDPOINT_MAP = {
    "alertas_epp": "/api/alertasepp/",
    "alertas_producto": "/api/alertasiventario/",
    "eventos_inventario": "/api/registroinventario/",
}


def process_event(topic: str, event_data: dict):
    """Preprocesa eventos según su tipo antes de enviar a FastAPI"""
    processed = event_data.copy()
    now_iso = datetime.now().isoformat()

    # Manejo especial para alertas EPP
    if topic == "alertas_epp":
        # Añadir timestamp si no viene en el evento
        if 'fecha' not in processed:
            processed['fecha'] = now_iso

    # Manejo especial para alertas de inventario
    elif topic == "alertas_inventario":
        # Asegurar campos necesarios
        if 'fecha' not in processed:
            processed['fecha'] = now_iso

        # Normalizar nombres de campos si es necesario
        field_mapping = {
            'producto_id': 'producto_codigo',
            'company_id': 'empresa_id',
            'sector': 'sector_id',
            'tipo': 'tipo_alerta'
        }

        for old_name, new_name in field_mapping.items():
            if old_name in processed:
                processed[new_name] = processed.pop(old_name)

    # Manejo para registros de inventario
    elif topic in ["registros_inventario", "inventario_updates"]:
        # Convertir fecha si es necesario
        if 'fecha' in processed and isinstance(processed['fecha'], str):
            try:
                # Intentar convertir a formato ISO (o dejarlo como está si ya es una fecha)
                processed['fecha'] = datetime.fromisoformat(processed['fecha']).date().isoformat()
            except:
                processed['fecha'] = datetime.now().date().isoformat()
        else:
            processed['fecha'] = datetime.now().date().isoformat()

        # Normalizar campos
        field_mapping = {
            'product_id': 'producto_codigo',
            'quantity': 'cantidad',
            'sector': 'sector_id',
            'company': 'empresa_id'
        }
        for old_name, new_name in field_mapping.items():
            if old_name in processed:
                processed[new_name] = processed.pop(old_name)

    # Manejo para productos por sector
    elif topic == "productos_sector":
        # Normalizar campos
        field_mapping = {
            'product_id': 'producto_codigo',
            'sector': 'sector_id',
            'company': 'empresa_id'
        }
        for old_name, new_name in field_mapping.items():
            if old_name in processed:
                processed[new_name] = processed.pop(old_name)

    return processed


def send_to_fastapi(endpoint, data):
    """Envía datos al endpoint FastAPI con reintentos"""
    url = f"{FASTAPI_BASE_URL}{endpoint}"

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, json=data, timeout=5)
            if response.status_code == 200:
                return True
            logger.error(f"Error al almacenar evento (intento {attempt + 1}): {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión (intento {attempt + 1}): {str(e)}")

        time.sleep(RETRY_DELAY)

    logger.error(f"Fallo al enviar evento después de {MAX_RETRIES} intentos")
    return False


def consumir_eventos_kafka():
    """Consume eventos de Kafka y los envía a los endpoints correspondientes"""
    conf = {
        'bootstrap.servers': KAFKA_BROKER,
        'group.id': 'grupo_servicio_general',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False,
        'max.poll.interval.ms': 300000  # 5 minutos
    }

    consumer = Consumer(conf)
    consumer.subscribe(list(TOPIC_ENDPOINT_MAP.keys()))

    logger.info("Iniciando consumidor Kafka en segundo plano...")
    logger.info(f"Topics suscritos: {list(TOPIC_ENDPOINT_MAP.keys())}")

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                logger.error(f"Error de Kafka: {msg.error()}")
                continue

            try:
                topic = msg.topic()
                raw_data = msg.value().decode('utf-8')
                event_data = json.loads(raw_data)
                logger.info(f"Evento recibido en topic '{topic}': {event_data}")

                # Obtener el endpoint correspondiente
                endpoint = TOPIC_ENDPOINT_MAP.get(topic)
                if not endpoint:
                    logger.warning(f"Topic '{topic}' no tiene endpoint configurado")
                    continue

                # Preprocesar evento según su tipo
                processed_data = process_event(topic, event_data)

                # Enviar al endpoint FastAPI con reintentos
                success = send_to_fastapi(endpoint, processed_data)

                if success:
                    consumer.commit(msg)  # Confirmar offset solo si fue exitoso
                    logger.info(f"Evento almacenado exitosamente en {endpoint}")
                else:
                    logger.error(f"No se pudo almacenar evento de topic '{topic}'")

            except json.JSONDecodeError as e:
                logger.error(f"Error decodificando JSON: {str(e)} - Raw: {raw_data}")
            except Exception as e:
                logger.exception(f"Error procesando mensaje: {str(e)}")

    except KeyboardInterrupt:
        logger.info("Deteniendo consumidor Kafka...")
    except Exception as e:
        logger.exception(f"Error fatal en consumidor Kafka: {str(e)}")
    finally:
        try:
            consumer.close()
        except Exception as e:
            logger.error(f"Error cerrando consumidor: {str(e)}")


# Iniciar el consumidor en un hilo separado al arrancar la app
@app.on_event("startup")
def startup_event():
    if os.getenv("ENABLE_KAFKA_CONSUMER", "true").lower() == "true":
        logger.info("Iniciando consumidor Kafka en segundo plano...")
        thread = threading.Thread(
            target=consumir_eventos_kafka,
            daemon=True,
            name="KafkaConsumerThread"
        )
        thread.start()
        logger.info("Consumidor Kafka iniciado")
    else:
        logger.info("Consumidor Kafka desactivado por configuración")


# Health check endpoint
@app.get("/health")
def health_check():
    return {
        "status": "OK",
        "kafka_consumer": os.getenv("ENABLE_KAFKA_CONSUMER", "true").lower() == "true"
    }