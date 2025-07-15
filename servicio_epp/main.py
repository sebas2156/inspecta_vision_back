from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from confluent_kafka import Consumer, Producer
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models import Camaras, Regiones, ReglasEpp, Suscripciones, ModelosIa
from ultralytics import YOLO
import cv2
import threading
import torch
import numpy as np
import time
import ast
from collections import defaultdict
from shapely.geometry import Point, Polygon
import json
import uvicorn
import asyncio
import base64
import io
from PIL import Image
import re

GPU_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

app = FastAPI()

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def punto_en_poligono(punto, poligono):
    if not poligono or len(poligono) < 3:
        return False

    point = Point(punto)
    try:
        polygon = Polygon(poligono)
        return polygon.contains(point)
    except Exception:
        return False


def imagen_a_base64(imagen, formato='JPEG', calidad=85):
    """Convierte una imagen OpenCV a base64"""
    if imagen is None or imagen.size == 0:
        return None

    # Convertir de BGR a RGB
    imagen_rgb = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)

    # Convertir a PIL Image
    pil_img = Image.fromarray(imagen_rgb)

    # Crear buffer en memoria
    buffer = io.BytesIO()
    pil_img.save(buffer, format=formato, quality=calidad)

    # Convertir a base64
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


class GPUCameraStream:
    def __init__(self, source, cam_id, empresa_id=None):
        self.source = source
        self.cam_id = cam_id
        self.empresa_id = empresa_id  # Nuevo campo para empresa_id
        self.regions = []  # Almacena diccionarios de regiones
        self.objeto_alertado = defaultdict(lambda: defaultdict(bool))
        self.last_seen = defaultdict(float)

        self.cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()
        print(f"Cámara {cam_id} iniciada en {source}")

    def _scale_polygon(self, polygon, frame_width, frame_height):
        if not polygon:
            return []

        scaled_poly = []
        for point in polygon:
            # Manejar diferentes formatos de puntos
            if isinstance(point, (list, tuple)) and len(point) >= 2:
                x, y = point[0], point[1]
            else:
                continue

            # Escalar coordenadas si están normalizadas
            if 0 <= x <= 1 and 0 <= y <= 1:
                scaled_x = int(x * frame_width)
                scaled_y = int(y * frame_height)
            else:
                scaled_x = int(x)
                scaled_y = int(y)

            scaled_poly.append((scaled_x, scaled_y))

        if len(scaled_poly) > 2 and scaled_poly[0] != scaled_poly[-1]:
            scaled_poly.append(scaled_poly[0])

        return scaled_poly

    def update(self):
        while self.running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    print(f"Reconectando a {self.source}...")
                    self.cap.release()
                    time.sleep(5)
                    self.cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
                    continue
                self.frame = frame
            except Exception as e:
                print(f"Error leyendo la cámara {self.source}: {e}")
                time.sleep(5)

    def get_frame(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def update_region(self, region_id, polygon=None, sector_id=None, restrictions=None, rule_id=None):
        with self.lock:
            # Buscar región existente
            region = next((r for r in self.regions if r['region_id'] == region_id), None)

            if region:
                print(f"Actualizando región {region_id} en cámara {self.cam_id}")
                # Actualizar solo los campos proporcionados
                if polygon is not None:
                    print(f" - Nuevo polígono: {polygon}")
                    region['polygon'] = polygon
                if sector_id is not None:
                    print(f" - Nuevo sector: {sector_id}")
                    region['sector_id'] = sector_id
                if restrictions is not None:
                    print(f" - Nuevas restricciones: {restrictions}")
                    region['restrictions'] = restrictions
                if rule_id is not None:
                    print(f" - Nuevo rule_id: {rule_id}")
                    region['rule_id'] = rule_id
            else:
                print(f"Creando nueva región {region_id} en cámara {self.cam_id}")
                # Crear nueva región si no existe
                if polygon is None:
                    polygon = []
                if restrictions is None:
                    restrictions = []
                self.regions.append({
                    'region_id': region_id,
                    'polygon': polygon,
                    'sector_id': sector_id,
                    'rule_id': rule_id,
                    'restrictions': restrictions
                })

    def remove_region(self, region_id):
        with self.lock:
            print(f"Eliminando región {region_id} de cámara {self.cam_id}")
            self.regions = [r for r in self.regions if r['region_id'] != region_id]

    def reset_estados_objeto(self, track_id):
        if track_id in self.objeto_alertado:
            del self.objeto_alertado[track_id]
        if track_id in self.last_seen:
            del self.last_seen[track_id]

    def release(self):
        print(f"Liberando cámara {self.cam_id}")
        self.running = False
        self.thread.join()
        self.cap.release()


class CameraManager:
    def __init__(self, model_path, model_id):
        print(f"Iniciando CameraManager para modelo {model_id} con ruta {model_path}")
        self.model = YOLO(model_path).to(GPU_DEVICE)
        self.model_id = model_id
        self.cameras = {}
        self.sector_rules = defaultdict(dict)
        self.lock = threading.Lock()
        self.last_frames = {}
        self.running = True
        self.thread = threading.Thread(target=self.process, daemon=True)
        self.thread.start()
        self.kafka_producer = Producer({'bootstrap.servers': 'localhost:9092'})
        print(f"Modelo {model_id} cargado y listo")

    def emitir_alerta_kafka(self, data):
        try:
            self.kafka_producer.produce('alertas_epp', json.dumps(data).encode('utf-8'))
            self.kafka_producer.flush()
        except Exception as e:
            print(f"Error al emitir evento Kafka: {e}")

    def handle_event(self, evento):
        tipo = evento["tipo"]
        accion = evento.get("accion", "desconocida")
        print(f"\n{'=' * 50}")
        print(f"Recibido evento: {tipo} - {accion}")
        print(f"Contenido: {evento}")
        print(f"{'=' * 50}\n")

        if tipo == "camara":
            self._handle_camera_event(evento)
        elif tipo == "region":
            self._handle_region_event(evento)
        elif tipo == "regla_epp":
            self._handle_rule_event(evento)
        else:
            print(f"Tipo de evento no reconocido: {tipo}")

    def _handle_camera_event(self, evento):
        cam_id = evento["id"]
        accion = evento["accion"]
        ip = evento["ip"]
        empresa_id = evento.get("empresa_id")  # Nuevo campo para empresa_id

        print(f"Procesando evento de cámara: {accion} - {cam_id}")

        if accion == "eliminado":
            if cam_id in self.cameras:
                self.cameras[cam_id].release()
                del self.cameras[cam_id]
                with self.lock:
                    if cam_id in self.last_frames:
                        del self.last_frames[cam_id]
            return

        if accion == "agregado":
            if cam_id not in self.cameras:
                # Crear cámara con empresa_id si está disponible
                self.cameras[cam_id] = GPUCameraStream(ip, cam_id, empresa_id)
        elif accion == "modificado":
            if cam_id in self.cameras:
                # Solo reiniciamos si la IP cambió
                if self.cameras[cam_id].source != ip:
                    self.cameras[cam_id].release()
                    self.cameras[cam_id] = GPUCameraStream(ip, cam_id, empresa_id)

    def _handle_region_event(self, evento):
        cam_id = evento["camara_id"]
        region_id = evento["id"]
        accion = evento["accion"]

        print(f"Procesando evento de región: {accion} - {region_id} en cámara {cam_id}")

        if cam_id not in self.cameras:
            print(f"Error: Cámara {cam_id} no encontrada para región {region_id}")
            return  # Cámara no existe

        if accion == "eliminado":
            self.cameras[cam_id].remove_region(region_id)
            return

        # Para agregado o modificado
        polygon = evento.get("coordenadas")
        sector_id = evento.get("sector_id")
        restrictions = evento.get("restricciones")
        rule_id = evento.get("regla_id")

        # Convertir coordenadas si vienen como string
        if isinstance(polygon, str):
            try:
                polygon = self.parse_coordenadas(polygon)
            except Exception as e:
                print(f"Error parseando coordenadas: {e}")
                polygon = []

        self.cameras[cam_id].update_region(
            region_id,
            polygon,
            sector_id,
            restrictions,
            rule_id
        )

    def parse_coordenadas(self, coord_str):
        """Convierte una cadena de coordenadas en una lista de tuplas"""
        # Ejemplo: "[(468.0, 5.0), (718.0, 5.0), (718.0, 445.0), (468.0, 445.0), (468.0, 5.0)]"
        try:
            # Usar ast.literal_eval para convertir la cadena en una lista de tuplas
            parsed = ast.literal_eval(coord_str)
            # Asegurarnos de que sea una lista de tuplas
            if isinstance(parsed, list):
                return [tuple(map(float, point)) for point in parsed]
            return []
        except (ValueError, SyntaxError):
            # Si falla, intentar con un método alternativo
            return self.alternative_parse(coord_str)

    def alternative_parse(self, coord_str):
        """Método alternativo para parsear coordenadas"""
        # Eliminar espacios innecesarios y los paréntesis exteriores
        clean_str = coord_str.strip()[1:-1]
        # Dividir en puntos individuales
        points = re.findall(r'\([^)]+\)', clean_str)
        result = []
        for point in points:
            # Eliminar paréntesis del punto
            point = point.strip()[1:-1]
            # Dividir en coordenadas x e y
            coords = point.split(',')
            if len(coords) >= 2:
                try:
                    x = float(coords[0].strip())
                    y = float(coords[1].strip())
                    result.append((x, y))
                except ValueError:
                    continue
        return result

    def _handle_rule_event(self, evento):
        sector_id = evento["sector_id"]
        rule_id = evento["regla_id"]
        restrictions = evento["restricciones"]

        print(f"Actualizando regla {rule_id} para sector {sector_id}")

        # Actualizar reglas globales
        self.sector_rules[sector_id][rule_id] = restrictions

        # Actualizar cámaras afectadas
        for cam in self.cameras.values():
            for region in cam.regions:
                if region.get('rule_id') == rule_id:
                    region['restrictions'] = restrictions
                    print(f"Regla actualizada en región {region['region_id']} de cámara {cam.cam_id}")

    def process(self):
        print(f"Iniciando procesamiento para modelo {self.model_id}")
        while self.running:
            current_time = time.time()
            with self.lock:
                cameras_copy = list(self.cameras.items())

            for cam_id, cam in cameras_copy:
                frame = cam.get_frame()
                if frame is None:
                    continue

                # Guardar una copia del frame original para capturas
                original_frame = frame.copy()

                results = self.model.track(
                    source=frame,
                    persist=True,
                    tracker="bytetrack.yaml",
                    verbose=False
                )

                if results and len(results) > 0:
                    annotated = results[0].plot()
                    height, width = frame.shape[:2]

                    # Dibujar todas las regiones
                    for region in cam.regions:
                        try:
                            scaled_poly = cam._scale_polygon(region['polygon'], width, height)
                            if len(scaled_poly) >= 3:  # Necesitamos al menos 3 puntos para un polígono
                                pts = np.array(scaled_poly, np.int32).reshape((-1, 1, 2))
                                cv2.polylines(annotated, [pts], True, (0, 255, 0), 2)
                                # Dibujar ID de región
                                if scaled_poly:
                                    cv2.putText(annotated, f"R{region['region_id']}",
                                                scaled_poly[0],
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                            else:
                                print(
                                    f"Advertencia: Polígono de región {region['region_id']} tiene {len(scaled_poly)} puntos (mínimo 3 requeridos)")
                        except Exception as e:
                            print(f"Error dibujando región {region.get('region_id', '?')}: {e}")

                    boxes = results[0].boxes.xyxy.cpu().numpy()
                    class_ids = results[0].boxes.cls.cpu().numpy()
                    track_ids = results[0].boxes.id.cpu().numpy().astype(int) if results[
                                                                                     0].boxes.id is not None else [-1] * len(
                        boxes)
                    class_names = self.model.names

                    for track_id in track_ids:
                        cam.last_seen[track_id] = current_time

                    for box, cls_id, track_id in zip(boxes, class_ids, track_ids):
                        x1, y1, x2, y2 = map(int, box)
                        cx = int((x1 + x2) / 2)
                        cy = int((y1 + y2) / 2)

                        cv2.circle(annotated, (cx, cy), 5, (0, 0, 255), -1)

                        for region in cam.regions:
                            try:
                                scaled_poly = cam._scale_polygon(region['polygon'], width, height)
                                if len(scaled_poly) < 3:  # Saltar polígonos inválidos
                                    continue

                                if punto_en_poligono((cx, cy), scaled_poly):
                                    detected_class = class_names[int(cls_id)]
                                    sector_id = region['sector_id']
                                    restrictions = region['restrictions']

                                    if (not cam.objeto_alertado[track_id][region['region_id']] and
                                            detected_class in restrictions):

                                        cam.objeto_alertado[track_id][region['region_id']] = True

                                        # Capturar imagen del objeto detectado
                                        obj_img = None
                                        try:
                                            # Ajustar coordenadas para no salir de los límites
                                            h, w = original_frame.shape[:2]
                                            x1_crop = max(0, x1 - 50)  # Margen adicional
                                            y1_crop = max(0, y1 - 50)
                                            x2_crop = min(w, x2 + 50)
                                            y2_crop = min(h, y2 + 50)

                                            # Recortar la región del objeto
                                            obj_img = original_frame[y1_crop:y2_crop, x1_crop:x2_crop]
                                        except Exception as e:
                                            print(f"Error capturando imagen: {e}")
                                            obj_img = None

                                        # Convertir imagen a base64
                                        imagen_base64 = imagen_a_base64(obj_img) if obj_img is not None else None

                                        alerta = {
                                            "tipo": "alerta_epp",
                                            "modelo_id": self.model_id,
                                            "camara_id": cam_id,
                                            "sector_id": sector_id,
                                            "tipo_incumplimiento": detected_class,
                                            "imagen": imagen_base64,  # Imagen en base64
                                            "regla_id": region.get('rule_id'),  # Opcional
                                            "empresa_id": cam.empresa_id  # Nuevo campo
                                        }
                                        print(f"ALERTA: {alerta}")
                                        self.emitir_alerta_kafka(alerta)

                                        # Dibujar alerta en el frame anotado
                                        cv2.putText(annotated, f"ALERTA: {detected_class}", (x1, y1 - 10),
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
                            except Exception as e:
                                print(f"Error procesando región: {e}")

                    # Limpiar estados de objetos desaparecidos
                    for track_id in list(cam.objeto_alertado.keys()):
                        if current_time - cam.last_seen.get(track_id, 0) > 5:
                            cam.reset_estados_objeto(track_id)

                    with self.lock:
                        self.last_frames[cam_id] = annotated.copy()
                else:
                    # Dibujar regiones incluso sin detecciones
                    annotated = frame.copy()
                    height, width = frame.shape[:2]

                    for region in cam.regions:
                        try:
                            scaled_poly = cam._scale_polygon(region['polygon'], width, height)
                            if len(scaled_poly) >= 3:  # Necesitamos al menos 3 puntos para un polígono
                                pts = np.array(scaled_poly, np.int32).reshape((-1, 1, 2))
                                cv2.polylines(annotated, [pts], True, (0, 255, 0), 2)
                                # Dibujar ID de región
                                if scaled_poly:
                                    cv2.putText(annotated, f"R{region['region_id']}",
                                                scaled_poly[0],
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                        except Exception as e:
                            print(f"Error dibujando región {region.get('region_id', '?')}: {e}")

                    with self.lock:
                        self.last_frames[cam_id] = annotated.copy()

            time.sleep(0.01)

    def stop(self):
        print(f"Deteniendo CameraManager para modelo {self.model_id}")
        self.running = False
        self.thread.join()
        with self.lock:
            for cam in self.cameras.values():
                cam.release()
            self.last_frames.clear()


def obtener_configuracion_camaras(db: Session):
    try:
        resultados = (
            db.query(
                Camaras.id.label('camara_id'),
                Camaras.ip,
                ModelosIa.id.label('modelo_id'),
                ModelosIa.ruta_modelo,
                Regiones.id.label('region_id'),
                Regiones.coordenadas,
                ReglasEpp.regla_id,
                ReglasEpp.restricciones_equipamiento,
                Regiones.sector_id,
                Camaras.empresa_id  # Nuevo campo para empresa_id
            )
            .join(Regiones, Camaras.id == Regiones.camara_id)
            .join(ReglasEpp, ReglasEpp.sector_id == Regiones.sector_id)
            .join(Suscripciones, Suscripciones.id == ReglasEpp.suscripcion_id)
            .join(ModelosIa, ModelosIa.id == Suscripciones.modelo_id)
            .all()
        )

        config = defaultdict(lambda: defaultdict(lambda: {
            "ip": None,
            "regions": [],
            "ruta_modelo": None,
            "empresa_id": None  # Nuevo campo
        }))

        for row in resultados:
            modelo_id = row.modelo_id
            cam_id = row.camara_id

            if config[modelo_id][cam_id]["ip"] is None:
                config[modelo_id][cam_id]["ip"] = row.ip
                config[modelo_id][cam_id]["ruta_modelo"] = row.ruta_modelo
                config[modelo_id][cam_id]["empresa_id"] = row.empresa_id  # Guardar empresa_id

            try:
                # Parsear coordenadas si vienen como string
                polygon = row.coordenadas
                if isinstance(polygon, str):
                    # Intentar parsear con ast.literal_eval
                    try:
                        polygon = ast.literal_eval(polygon)
                    except:
                        # Si falla, usar método alternativo
                        polygon = parse_coordenadas_string(polygon)

                # Filtrar puntos inválidos
                valid_polygon = []
                for point in polygon:
                    # Asegurar que cada punto tenga 2 coordenadas
                    if isinstance(point, (list, tuple)) and len(point) >= 2:
                        valid_polygon.append((point[0], point[1]))

                if len(valid_polygon) >= 3:
                    restrictions = row.restricciones_equipamiento
                    if isinstance(restrictions, str):
                        try:
                            restrictions = ast.literal_eval(restrictions)
                        except:
                            restrictions = []

                    config[modelo_id][cam_id]["regions"].append({
                        "region_id": row.region_id,
                        "polygon": valid_polygon,
                        "sector_id": row.sector_id,
                        "rule_id": row.regla_id,
                        "restrictions": restrictions
                    })
                    print(f"Región {row.region_id} añadida a cámara {cam_id}")
                else:
                    print(
                        f"Advertencia: Polígono para región {row.region_id} no tiene suficientes puntos ({len(valid_polygon)})")
            except Exception as e:
                print(f"Error procesando región: {e}")

        lista_final = []
        for modelo_id, camaras in config.items():
            dispositivos = []
            for cam_id, datos in camaras.items():
                dispositivos.append({
                    "cam_id": cam_id,
                    "ip": datos["ip"],
                    "regions": datos["regions"],
                    "ruta_modelo": datos["ruta_modelo"],
                    "empresa_id": datos["empresa_id"]  # Nuevo campo
                })

            lista_final.append({
                "modelo_id": modelo_id,
                "dispositivos": dispositivos
            })

        return lista_final

    except Exception as e:
        raise Exception(f"Error BD: {str(e)}")


def parse_coordenadas_string(coord_str):
    """Convierte una cadena de coordenadas en una lista de tuplas"""
    # Ejemplo: "[(468.0, 5.0), (718.0, 5.0), (718.0, 445.0), (468.0, 445.0), (468.0, 5.0)]"
    try:
        # Usar expresión regular para extraer puntos
        points = re.findall(r'\(([^)]+)\)', coord_str)
        result = []
        for point in points:
            # Dividir en coordenadas x e y
            coords = point.split(',')
            if len(coords) >= 2:
                try:
                    x = float(coords[0].strip())
                    y = float(coords[1].strip())
                    result.append((x, y))
                except ValueError:
                    continue
        return result
    except Exception:
        return []


@app.get("/video_feed/{model_id}/{cam_id}")
async def video_feed(model_id: int, cam_id: int):
    if not hasattr(app.state, "camera_managers"):
        raise HTTPException(status_code=503, detail="Sistema no inicializado")

    manager = app.state.camera_managers.get(model_id)
    if not manager:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")

    with manager.lock:
        if cam_id not in manager.cameras:
            raise HTTPException(
                status_code=404,
                detail="Cámara no asociada a este modelo"
            )

    async def generate_frames():
        loop = asyncio.get_event_loop()
        while True:
            frame = None
            with manager.lock:
                frame = manager.last_frames.get(cam_id)

            if frame is not None:
                success, buffer = cv2.imencode('.jpg', frame)
                if success:
                    yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'
            await asyncio.sleep(0.033)

    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")


def main():
    print("Iniciando servicio de detección de EPP")
    db = next(get_db())
    configuracion = obtener_configuracion_camaras(db)

    if not configuracion:
        print("No hay configuraciones de cámaras")
        return

    camera_managers = {}
    camera_to_models = defaultdict(list)

    for model_config in configuracion:
        modelo_id = model_config['modelo_id']

        # Encontrar la ruta del modelo (todas las cámaras comparten modelo)
        modelo_path = model_config['dispositivos'][0]['ruta_modelo'] if model_config['dispositivos'] else None
        if not modelo_path:
            print(f"Advertencia: No se encontró ruta de modelo para modelo {modelo_id}")
            continue

        manager = CameraManager(modelo_path, modelo_id)
        camera_managers[modelo_id] = manager

        for dispositivo in model_config['dispositivos']:
            cam_id = dispositivo["cam_id"]
            camera_to_models[cam_id].append(modelo_id)

            # Evento para crear cámara con empresa_id
            manager.handle_event({
                "tipo": "camara",
                "accion": "agregado",
                "id": cam_id,
                "ip": dispositivo["ip"],
                "empresa_id": dispositivo["empresa_id"]  # Nuevo campo
            })

            # Eventos para crear regiones
            for region in dispositivo["regions"]:
                manager.handle_event({
                    "tipo": "region",
                    "accion": "agregado",
                    "id": region["region_id"],
                    "camara_id": cam_id,
                    "coordenadas": region["polygon"],
                    "sector_id": region["sector_id"],
                    "restricciones": region["restrictions"],
                    "regla_id": region.get("rule_id")  # Opcional
                })

    app.state.camera_managers = camera_managers
    print(
        f"Se iniciaron {len(camera_managers)} modelos con {sum(len(m.cameras) for m in camera_managers.values())} cámaras")

    def manejar_evento_kafka(evento_json):
        try:
            tipo = evento_json.get("tipo")
            modelos_afectados = set()

            # Propagación especial para cámaras nuevas
            if tipo == "camara" and evento_json.get("accion") == "agregado":
                cam_id = evento_json.get("id")
                # Asignar la cámara a todos los modelos
                if cam_id not in camera_to_models:
                    camera_to_models[cam_id] = list(camera_managers.keys())
                # Propagar a todos los managers
                modelos_afectados = set(camera_managers.keys())
            elif tipo == "camara":
                cam_id = evento_json.get("id")
                if cam_id in camera_to_models:
                    modelos_afectados = set(camera_to_models[cam_id])
            elif tipo == "region":
                cam_id = evento_json.get("camara_id")
                if cam_id in camera_to_models:
                    modelos_afectados = set(camera_to_models[cam_id])
            elif tipo == "regla_epp":
                # Afecta a todos los modelos
                modelos_afectados = set(camera_managers.keys())
            else:
                print(f"Tipo de evento no reconocido: {tipo}")
                return

            # Propagar evento a los managers afectados
            for modelo_id in modelos_afectados:
                if modelo_id in camera_managers:
                    camera_managers[modelo_id].handle_event(evento_json)

        except Exception as e:
            print(f"Error procesando evento: {str(e)}")

    def iniciar_consumidor_kafka():
        print("Iniciando consumidor Kafka en tema 'notificaciones'")
        config = {'bootstrap.servers': 'localhost:9092', 'group.id': 'grupo_epp', 'auto.offset.reset': 'latest'}
        consumer = Consumer(config)
        consumer.subscribe(['notificaciones'])

        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print("Error Kafka:", msg.error())
                continue

            try:
                evento = msg.value().decode('utf-8')
                evento_json = json.loads(evento)
                print(f"Evento recibido de Kafka: {evento_json}")
                manejar_evento_kafka(evento_json)
            except Exception as e:
                print("Error procesando evento Kafka:", e)

    kafka_thread = threading.Thread(target=iniciar_consumidor_kafka, daemon=True)
    kafka_thread.start()

    config = uvicorn.Config(app, host="0.0.0.0", port=8001)
    server = uvicorn.Server(config)
    print(f"Servidor FastAPI iniciado en http://0.0.0.0:8001")
    server.run()


if __name__ == "__main__":
    main()