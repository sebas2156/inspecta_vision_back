from confluent_kafka import Consumer
from confluent_kafka import Producer
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models import Camaras, Regiones, ReglasEpp, Suscripciones, ModelosIa, Logs
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

GPU_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def punto_en_poligono(punto, poligono):
    point = Point(punto)
    polygon = Polygon(poligono)
    return polygon.contains(point)


class GPUCameraStream:
    def __init__(self, source, polygons=None, restricciones=None, sector_ids=None):
        self.source = source
        self.original_polygons = polygons or []
        self.restricciones = restricciones or []
        self.sector_ids = sector_ids or []

        self.cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def _parse_polygons(self):
        return [polygon for polygon in self.original_polygons if len(polygon) >= 3]

    def _scale_polygons(self, frame_width, frame_height):
        scaled = []
        for polygon in self._parse_polygons():
            scaled_poly = []
            for point in polygon:
                x, y = point
                if 0 <= x <= 1 and 0 <= y <= 1:
                    scaled_x = int(x * frame_width)
                    scaled_y = int(y * frame_height)
                else:
                    scaled_x = int(x)
                    scaled_y = int(y)
                scaled_poly.append((scaled_x, scaled_y))

            if len(scaled_poly) > 2 and scaled_poly[0] != scaled_poly[-1]:
                scaled_poly.append(scaled_poly[0])

            scaled.append(scaled_poly)
        return scaled

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

    def update_config(self, polygons, restricciones, sector_ids):
        with self.lock:
            self.original_polygons = polygons
            self.restricciones = restricciones
            self.sector_ids = sector_ids

    def release(self):
        self.running = False
        self.thread.join()
        self.cap.release()


class CameraManager:
    def __init__(self, model_path, model_id):
        self.model = YOLO(model_path).to(GPU_DEVICE)
        self.model_id = model_id
        self.cameras = {}
        self.sector_rules = defaultdict(dict)
        self.sector_products = defaultdict(dict)
        self.lock = threading.Lock()
        self.running = True
        self.thread = threading.Thread(target=self.process, daemon=True)
        self.thread.start()
        self.kafka_producer = Producer({'bootstrap.servers': 'localhost:9092'})

    def emitir_alerta_kafka(self, data):
        try:
            self.kafka_producer.produce('alertas_epp', json.dumps(data).encode('utf-8'))
            self.kafka_producer.flush()
        except Exception as e:
            print(f"Error al emitir evento Kafka: {e}")

    def handle_event(self, evento):
        if evento["tipo"] == "camara":
            self._handle_camera_event(evento)
        elif evento["tipo"] == "regla_epp":
            self._handle_rule_event(evento)
        elif evento["tipo"] == "sector":
            self._handle_sector_event(evento)

    def _handle_camera_event(self, evento):
        cam_id = evento["id"]

        if evento["accion"] == "eliminado":
            if cam_id in self.cameras:
                self.cameras[cam_id].release()
                del self.cameras[cam_id]
            return

        polygons = []
        restricciones = []
        sector_ids = []

        for region in evento.get("regiones", []):
            try:
                coords = region["coordenadas"]
                if len(coords) < 3:
                    continue

                if coords[0] != coords[-1]:
                    coords.append(coords[0])

                polygons.append(coords)
                restricciones.append(region.get("restricciones_epp", []))
                sector_ids.append(region.get("sector_id", 0))
            except KeyError:
                continue

        with self.lock:
            if cam_id in self.cameras:
                self.cameras[cam_id].update_config(polygons, restricciones, sector_ids)
            else:
                self.cameras[cam_id] = GPUCameraStream(
                    source=evento["ip"],
                    polygons=polygons,
                    restricciones=restricciones,
                    sector_ids=sector_ids
                )

    def _handle_rule_event(self, evento):
        sector_id = evento["sector_id"]
        new_rules = evento["restricciones"]

        with self.lock:
            self.sector_rules[sector_id] = new_rules
            for cam in self.cameras.values():
                for idx, s_id in enumerate(cam.sector_ids):
                    if s_id == sector_id:
                        cam.restricciones[idx] = new_rules

    def process(self):
        while self.running:
            with self.lock:
                cameras_copy = list(self.cameras.items())

            for cam_id, cam in cameras_copy:
                frame = cam.get_frame()
                if frame is None:
                    continue

                results = self.model.track(
                    source=frame,
                    persist=True,
                    tracker="bytetrack.yaml",
                    verbose=False
                )

                if results and len(results) > 0:
                    annotated = results[0].plot()
                    height, width = frame.shape[:2]

                    polygons = cam._scale_polygons(width, height)
                    for poly in polygons:
                        pts = np.array(poly, np.int32).reshape((-1, 1, 2))
                        cv2.polylines(annotated, [pts], True, (0, 255, 0), 2)

                    boxes = results[0].boxes.xyxy.cpu().numpy()
                    class_ids = results[0].boxes.cls.cpu().numpy()
                    class_names = self.model.names

                    for box, cls_id in zip(boxes, class_ids):
                        x1, y1, x2, y2 = map(int, box)
                        cx = int((x1 + x2) / 2)
                        cy = int((y1 + y2) / 2)

                        # Dibujar punto central
                        cv2.circle(annotated, (cx, cy), 5, (0, 0, 255), -1)

                        for poly_idx, (poly, restrictions) in enumerate(zip(polygons, cam.restricciones)):
                            if punto_en_poligono((cx, cy), poly):
                                detected_class = class_names[int(cls_id)]
                                if detected_class in restrictions:
                                    sector_id = cam.sector_ids[poly_idx] if poly_idx < len(cam.sector_ids) else "N/A"
                                    alerta = {
                                        "tipo": "alerta_epp",
                                        "modelo_id": self.model_id,
                                        "camara_id": cam_id,
                                        "sector_id": sector_id,
                                        "clase_detectada": detected_class,
                                        "timestamp": time.time()
                                    }
                                    print(f"ALERTA: {alerta}")
                                    self.emitir_alerta_kafka(alerta)
                                    cv2.putText(annotated, f"ALERTA: {detected_class}", (x1, y1 - 10),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

                    cv2.imshow(f"Cámara {cam_id} - Modelo {self.model_id}", annotated)

            if cv2.waitKey(1) == 27:
                self.stop()
                break
            time.sleep(0.01)

    def stop(self):
        self.running = False
        self.thread.join()
        with self.lock:
            for cam in self.cameras.values():
                cam.release()
        cv2.destroyAllWindows()


def obtener_configuracion_camaras(db: Session):
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

            try:
                polygon = ast.literal_eval(row.coordenadas) if isinstance(row.coordenadas, str) else []
                if isinstance(polygon, list) and len(polygon) >= 3:
                    config[modelo_id][cam_id]["polygons"].append(polygon)
            except Exception:
                pass

            try:
                restricciones = ast.literal_eval(row.restricciones_equipamiento) if isinstance(row.restricciones_equipamiento, str) else []
                if isinstance(restricciones, list):
                    config[modelo_id][cam_id]["restricciones"].extend(restricciones)
            except Exception:
                pass

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
                "ruta_modelo": datos["ruta_modelo"],  # Correcto: todos los datos de esa cámara usan la misma ruta
                "dispositivos": dispositivos
            })

        return lista_final

    except Exception as e:
        raise Exception(f"Error BD: {str(e)}")


def main():
    db = next(get_db())
    configuracion = obtener_configuracion_camaras(db)

    if not configuracion:
        print("No hay configuraciones de cámaras")
        return

    camera_managers = {}
    camera_to_models = defaultdict(list)

    # Crear managers y mapeo cámara-modelo
    for model_config in configuracion:
        modelo_id = model_config['modelo_id']
        modelo_path = model_config['ruta_modelo']

        manager = CameraManager(modelo_path, modelo_id)
        camera_managers[modelo_id] = manager

        for dispositivo in model_config['dispositivos']:
            cam_id = dispositivo["cam_id"]
            camera_to_models[cam_id].append(modelo_id)

            regiones = []
            for polygon, restriccion, sector_id in zip(
                    dispositivo["polygons"],
                    dispositivo["restricciones"],
                    dispositivo["sector_ids"]
            ):
                regiones.append({
                    "coordenadas": polygon,
                    "restricciones_epp": restriccion,
                    "sector_id": sector_id
                })

            manager.handle_event({
                "tipo": "camara",
                "accion": "agregado",
                "id": cam_id,
                "ip": dispositivo["ip"],
                "regiones": regiones
            })

    # Configurar consumidor Kafka
    def manejar_evento_kafka(evento_json):
        try:
            required_fields = {
                "camara": ["id", "ip", "regiones"],
                "regla_epp": ["sector_id", "restricciones"],
                "sector": ["sector_id", "productos"]
            }

            tipo = evento_json.get("tipo")
            if tipo not in required_fields:
                raise ValueError(f"Tipo de evento inválido: {tipo}")

            for field in required_fields[tipo]:
                if field not in evento_json:
                    raise ValueError(f"Campo requerido faltante: {field}")

            if tipo == "camara":
                cam_id = evento_json["id"]
                for modelo_id in camera_to_models.get(cam_id, []):
                    camera_managers[modelo_id].handle_event(evento_json)
            else:
                for manager in camera_managers.values():
                    manager.handle_event(evento_json)

        except Exception as e:
            print(f"Error procesando evento: {str(e)}")
            db = next(get_db())
            db.add(Logs(
                cuenta_id=0,
                accion="ErrorKafka",
                detalles=json.dumps({
                    "error": str(e),
                    "evento": evento_json
                })
            ))
            db.commit()

    def iniciar_consumidor_kafka():
        config = {'bootstrap.servers': 'localhost:9092', 'group.id': 'grupo_detencion', 'auto.offset.reset': 'latest'}
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
                manejar_evento_kafka(evento_json)
            except Exception as e:
                print("Error procesando evento Kafka:", e)

    kafka_thread = threading.Thread(target=iniciar_consumidor_kafka, daemon=True)
    kafka_thread.start()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nDeteniendo sistema...")
        for manager in camera_managers.values():
            manager.stop()
        print("Sistema detenido correctamente")


if __name__ == "__main__":
    main()