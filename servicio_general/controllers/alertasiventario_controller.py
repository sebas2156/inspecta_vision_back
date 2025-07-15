from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models.alertasinventario import AlertasInventario
from servicio_general.schemas.alertasinventario_schema import AlertasInventarioCreate, AlertasInventarioResponse
from shared.schemas.paginacion import PaginatedResponse
from datetime import datetime
import base64
import os
import uuid
from pathlib import Path
from fastapi.responses import FileResponse
from typing import List

router = APIRouter()

# Configuración de directorio para imágenes
IMAGES_DIR = "imagenes_alertas"
Path(IMAGES_DIR).mkdir(parents=True, exist_ok=True)  # Crear directorio si no existe


def save_base64_image(base64_str: str) -> str:
    """Guarda una imagen en base64 y devuelve la ruta relativa"""
    try:
        # Generar nombre único para el archivo
        image_name = f"{uuid.uuid4()}.jpg"
        image_path = os.path.join(IMAGES_DIR, image_name)

        # Decodificar base64 y guardar
        image_data = base64.b64decode(base64_str)
        with open(image_path, "wb") as image_file:
            image_file.write(image_data)

        return image_path
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando imagen: {str(e)}"
        )


@router.post("/", response_model=AlertasInventarioResponse)
def crear_alertasinventario(alertasinventario: AlertasInventarioCreate, db: Session = Depends(get_db)):
    # Procesar imagen si está presente
    image_path = None
    if alertasinventario.imagen:
        image_path = save_base64_image(alertasinventario.imagen)

    # Crear nueva alerta
    nueva_alertasinventario = AlertasInventario(
        sector_id=alertasinventario.sector_id,
        producto_codigo=alertasinventario.producto_codigo,
        empresa_id=alertasinventario.empresa_id,
        tipo_alerta=alertasinventario.tipo_alerta,
        imagen=image_path,  # Guardar ruta en lugar de base64
        fecha=alertasinventario.fecha or datetime.now()
    )

    db.add(nueva_alertasinventario)
    db.commit()
    db.refresh(nueva_alertasinventario)
    return nueva_alertasinventario


@router.get("/", response_model=PaginatedResponse[AlertasInventarioResponse])
def obtener_alertasinventario(
        request: Request,
        skip: int = 0,
        limit: int = 10,
        db: Session = Depends(get_db)
):
    # Obtenemos las alertasinventario con paginación
    total_registros = db.query(AlertasInventario).count()
    alertas = db.query(AlertasInventario).offset(skip).limit(limit).all()

    # Convertir a objetos Pydantic y añadir URL de imagen
    alertas_response = []
    for alerta in alertas:
        alerta_data = {
            "id": alerta.id,
            "sector_id": alerta.sector_id,
            "producto_codigo": alerta.producto_codigo,
            "empresa_id": alerta.empresa_id,
            "tipo_alerta": alerta.tipo_alerta,
            "imagen": alerta.imagen,
            "fecha": alerta.fecha,
            "imagen_url": None
        }

        # Generar URL completa para la imagen si existe
        if alerta.imagen:
            # Obtener solo el nombre del archivo de la ruta
            filename = Path(alerta.imagen).name
            alerta_data["imagen_url"] = str(request.url_for(
                "obtener_imagen_alertas",
                ruta_imagen=filename
            ))

        alertas_response.append(AlertasInventarioResponse(**alerta_data))

    total_paginas = (total_registros + limit - 1) // limit
    return PaginatedResponse(
        total_registros=total_registros,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=alertas_response
    )


@router.get("/{alertasinventario_id}", response_model=AlertasInventarioResponse)
def obtener_alertasinventario(
        request: Request,
        alertasinventario_id: int,
        db: Session = Depends(get_db)
):
    alerta = db.query(AlertasInventario).filter(AlertasInventario.id == alertasinventario_id).first()
    if not alerta:
        raise HTTPException(status_code=404, detail="AlertasInventario no encontrada.")

    alerta_data = {
        "id": alerta.id,
        "sector_id": alerta.sector_id,
        "producto_codigo": alerta.producto_codigo,
        "empresa_id": alerta.empresa_id,
        "tipo_alerta": alerta.tipo_alerta,
        "imagen": alerta.imagen,
        "fecha": alerta.fecha,
        "imagen_url": None
    }

    # Añadir URL de imagen si existe
    if alerta.imagen:
        filename = Path(alerta.imagen).name
        alerta_data["imagen_url"] = str(request.url_for(
            "obtener_imagen_alertas",
            ruta_imagen=filename
        ))

    return AlertasInventarioResponse(**alerta_data)


@router.put("/{alertasinventario_id}", response_model=AlertasInventarioResponse)
def actualizar_alertasinventario(
        alertasinventario_id: int,
        alerta_update: AlertasInventarioCreate,
        db: Session = Depends(get_db)
):
    alerta_existente = db.query(AlertasInventario).filter(AlertasInventario.id == alertasinventario_id).first()
    if not alerta_existente:
        raise HTTPException(status_code=404, detail="Alerta no encontrada.")

    # Procesar imagen si se proporciona nueva
    nueva_imagen_path = None
    if alerta_update.imagen:
        # Eliminar imagen anterior si existe
        if alerta_existente.imagen and os.path.exists(alerta_existente.imagen):
            try:
                os.remove(alerta_existente.imagen)
            except Exception as e:
                print(f"Error eliminando imagen anterior: {str(e)}")

        # Guardar nueva imagen
        nueva_imagen_path = save_base64_image(alerta_update.imagen)

    # Actualizar campos
    update_data = alerta_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        if key == "imagen":
            # Actualizar ruta de imagen si hay nueva
            if nueva_imagen_path:
                setattr(alerta_existente, key, nueva_imagen_path)
        elif key != "fecha" or value is not None:  # Ignorar fecha si no se proporciona
            setattr(alerta_existente, key, value)

    # Manejar fecha por separado
    if alerta_update.fecha:
        alerta_existente.fecha = alerta_update.fecha

    db.commit()
    db.refresh(alerta_existente)
    return alerta_existente


@router.delete("/{alertasinventario_id}", response_model=AlertasInventarioResponse)
def eliminar_alertasinventario(alertasinventario_id: int, db: Session = Depends(get_db)):
    alerta = db.query(AlertasInventario).filter(AlertasInventario.id == alertasinventario_id).first()
    if not alerta:
        raise HTTPException(status_code=404, detail="AlertasInventario no encontrada.")

    # Eliminar imagen asociada si existe
    if alerta.imagen and os.path.exists(alerta.imagen):
        try:
            os.remove(alerta.imagen)
        except Exception as e:
            # Registrar error pero continuar con la eliminación
            print(f"Error eliminando imagen: {str(e)}")

    db.delete(alerta)
    db.commit()
    return alerta


@router.get("/imagen/{ruta_imagen}", response_class=FileResponse)
async def obtener_imagen_alertas(ruta_imagen: str):
    """Endpoint para obtener imágenes de alertas"""
    image_path = Path(IMAGES_DIR) / ruta_imagen

    # Validar que la ruta esté dentro del directorio permitido
    if not image_path.exists() or IMAGES_DIR not in str(image_path.resolve()):
        raise HTTPException(status_code=404, detail="Imagen no encontrada")

    return FileResponse(image_path)