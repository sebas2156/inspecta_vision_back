from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import cv2
import torch
import threading
import time
import numpy as np
from typing import Optional
from database import get_db
from Models.producto import Producto
from io import BytesIO

# Configuración
CAMERAS = [
    "http://192.168.0.4:8080/video",  # Cámara IP
    0,  # Webcam 1
    1  # Webcam 2
]
TARGET_SIZE = (640, 480)  # Resolución para cada cámara
GPU_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

app = FastAPI()
router = APIRouter()

class GPUCameraStream:
    def __init__(self, source):
        self.cap = cv2.VideoCapture(source)
        self.frame_tensor = None
        self.running = True
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                # Mantener el espacio de color original (BGR)
                frame = cv2.resize(frame, TARGET_SIZE)
                tensor = torch.from_numpy(frame).float().to(GPU_DEVICE)
                tensor = tensor.permute(2, 0, 1) / 255.0  # CHW, normalized
                self.frame_tensor = tensor

    def get_frame(self):
        return self.frame_tensor.clone() if self.frame_tensor is not None else None

    def release(self):
        self.running = False
        self.thread.join()
        self.cap.release()


class GPUMerger:
    def __init__(self, sources):
        self.cameras = [GPUCameraStream(src) for src in sources]
        self.model = torch.hub.load('ultralytics/yolov8', 'yolov8n').to(GPU_DEVICE)
        self.model.fuse = False  # Desactivar fusión problemática

        if torch.cuda.is_available():
            # Usar autocast para mixed precision
            self.amp = True
            self.scaler = torch.cuda.amp.GradScaler(enabled=self.amp)
        else:
            self.amp = False

    def combine_gpu(self, tensors):
        # Combinar tensores en GPU (batch, channels, height, total_width)
        return torch.cat(tensors, dim=2).unsqueeze(0)

    def process_frame(self, frame, db: Session):
        # Inferencia con YOLO
        results = self.model(frame)
        detecciones = results.xywh[0].cpu().numpy()

        # Zona específica de detección
        zona_especifica = (100, 100, 500, 500)

        for deteccion in detecciones:
            x_center, y_center, w, h, confidence, class_id = deteccion
            x_min = int((x_center - w / 2) * frame.shape[1])
            y_min = int((y_center - h / 2) * frame.shape[0])
            x_max = int((x_center + w / 2) * frame.shape[1])
            y_max = int((y_center + h / 2) * frame.shape[0])

            if zona_especifica[0] < x_center * frame.shape[1] < zona_especifica[2] and zona_especifica[1] < y_center * frame.shape[0] < zona_especifica[3]:
                objeto_detectado = results.names[int(class_id)]
                producto = db.query(Producto).filter(Producto.nombre_producto == objeto_detectado).first()

                if producto:
                    print(f"Producto detectado: {producto.nombre_producto}")
                else:
                    nuevo_producto = Producto(
                        nombre_producto=objeto_detectado,
                        descripcion=f"Detectado en zona: ({zona_especifica})",
                        stock=1,
                        sector="Desconocido"
                    )
                    db.add(nuevo_producto)
                    db.commit()
                    db.refresh(nuevo_producto)
                    print(f"Nuevo producto agregado: {nuevo_producto.nombre_producto}")

        # Devolver el frame con las predicciones
        return results[0].plot()

    def process(self, db: Session):
        while True:
            frames = []
            for cam in self.cameras:
                frame_tensor = cam.get_frame()
                if frame_tensor is not None:
                    # Convertir tensor de GPU a BGR para usar en OpenCV
                    frame = frame_tensor.squeeze().permute(1, 2, 0).cpu().numpy()
                    frame = (frame * 255).astype(np.uint8)
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    frames.append(frame)

            if frames:
                # Fusionar los frames en un solo frame horizontalmente
                combined_frame = np.concatenate(frames, axis=1)

                # Procesar frame con el modelo
                processed_frame = self.process_frame(combined_frame, db)

                # Convertir el frame procesado en un buffer para streaming
                ret, buffer = cv2.imencode('.jpg', processed_frame)
                if not ret:
                    break
                frame_bytes = BytesIO(buffer.tobytes())
                yield frame_bytes.getvalue()

            time.sleep(0.1)


@router.get("/video/")
async def video_feed(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    sources = CAMERAS
    gpu_merger = GPUMerger(sources)
    background_tasks.add_task(gpu_merger.process, db)

    return StreamingResponse(gpu_merger.process(db), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/")
async def root():
    return {"mensaje": "API de detección en tiempo real."}


# Incluir el router en la aplicación principal de FastAPI
app.include_router(router)
