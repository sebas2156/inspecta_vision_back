from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models.alertasepp import AlertasEpp
from servicio_general.schemas.alertasepp_schema import AlertasEppCreate, AlertasEppResponse
from shared.schemas.paginacion import PaginatedResponse
from datetime import datetime
import base64
import os
import uuid
from pathlib import Path
from fastapi.responses import FileResponse

router = APIRouter()

# Configuración de directorio para imágenes de EPP
EPP_IMAGES_DIR = "imagenes_alertas_epp"
Path(EPP_IMAGES_DIR).mkdir(parents=True, exist_ok=True)


def save_base64_image_epp(base64_str: str) -> str:
    """Guarda una imagen en base64 y devuelve la ruta relativa para alertas EPP"""
    try:
        # Generar nombre único para el archivo con extensión
        image_name = f"{uuid.uuid4()}.jpg"
        image_path = Path(EPP_IMAGES_DIR) / image_name

        # Decodificar base64 y guardar
        image_data = base64.b64decode(base64_str)
        with open(image_path, "wb") as image_file:
            image_file.write(image_data)

        return str(image_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando imagen: {str(e)}"
        )


@router.post("/", response_model=AlertasEppResponse)
def crear_alertasepp(alertasepp: AlertasEppCreate, db: Session = Depends(get_db)):
    # Procesar imagen si está presente
    image_path = None
    if alertasepp.imagen:
        image_path = save_base64_image_epp(alertasepp.imagen)

    # Crear nueva alerta
    nueva_alertasepp = AlertasEpp(
        regla_id=alertasepp.regla_id,
        sector_id=alertasepp.sector_id,
        tipo_incumplimiento=alertasepp.tipo_incumplimiento,
        imagen=image_path,
        fecha=alertasepp.fecha or datetime.now()
    )

    db.add(nueva_alertasepp)
    db.commit()
    db.refresh(nueva_alertasepp)
    return nueva_alertasepp


@router.get("/", response_model=PaginatedResponse[AlertasEppResponse])
def obtener_alertasepp(
        request: Request,
        skip: int = 0,
        limit: int = 10,
        db: Session = Depends(get_db)
):
    # Obtenemos las alertasepp con paginación
    total_registros = db.query(AlertasEpp).count()
    alertas = db.query(AlertasEpp).offset(skip).limit(limit).all()

    # Convertir a objetos Pydantic y añadir URL de imagen
    alertas_response = []
    for alerta in alertas:
        alerta_data = {
            "id": alerta.id,
            "regla_id": alerta.regla_id,
            "sector_id": alerta.sector_id,
            "tipo_incumplimiento": alerta.tipo_incumplimiento,
            "imagen": alerta.imagen,
            "fecha": alerta.fecha,
            "imagen_url": None
        }

        # Generar URL completa para la imagen si existe
        if alerta.imagen:
            # Obtener solo el nombre del archivo de la ruta
            filename = Path(alerta.imagen).name
            alerta_data["imagen_url"] = str(request.url_for(
                "obtener_imagen_epp",
                ruta_imagen=filename
            ))

        alertas_response.append(AlertasEppResponse(**alerta_data))

    total_paginas = (total_registros + limit - 1) // limit
    return PaginatedResponse(
        total_registros=total_registros,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=alertas_response
    )


@router.get("/{alertasepp_id}", response_model=AlertasEppResponse)
def obtener_alertasepp(
        request: Request,
        alertasepp_id: int,
        db: Session = Depends(get_db)
):
    alerta = db.query(AlertasEpp).filter(AlertasEpp.id == alertasepp_id).first()
    if not alerta:
        raise HTTPException(status_code=404, detail="AlertasEpp no encontrada.")

    alerta_data = {
        "id": alerta.id,
        "regla_id": alerta.regla_id,
        "sector_id": alerta.sector_id,
        "tipo_incumplimiento": alerta.tipo_incumplimiento,
        "imagen": alerta.imagen,
        "fecha": alerta.fecha,
        "imagen_url": None
    }

    # Añadir URL de imagen si existe
    if alerta.imagen:
        filename = Path(alerta.imagen).name
        alerta_data["imagen_url"] = str(request.url_for(
            "obtener_imagen_epp",
            ruta_imagen=filename
        ))

    return AlertasEppResponse(**alerta_data)


@router.put("/{alertasepp_id}", response_model=AlertasEppResponse)
def actualizar_alertasepp(
        alertasepp_id: int,
        alerta_update: AlertasEppCreate,
        db: Session = Depends(get_db)
):
    alerta_existente = db.query(AlertasEpp).filter(AlertasEpp.id == alertasepp_id).first()
    if not alerta_existente:
        raise HTTPException(status_code=404, detail="Alerta EPP no encontrada.")

    # Procesar imagen si se proporciona nueva
    nueva_imagen_path = None
    if alerta_update.imagen:
        # Eliminar imagen anterior si existe
        if alerta_existente.imagen and Path(alerta_existente.imagen).exists():
            try:
                Path(alerta_existente.imagen).unlink()
            except Exception as e:
                print(f"Error eliminando imagen anterior: {str(e)}")

        # Guardar nueva imagen
        nueva_imagen_path = save_base64_image_epp(alerta_update.imagen)

    # Actualizar campos
    update_data = alerta_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        if key == "imagen":
            # Actualizar ruta de imagen si hay nueva
            if nueva_imagen_path:
                setattr(alerta_existente, key, nueva_imagen_path)
        elif key != "fecha" or value is not None:
            setattr(alerta_existente, key, value)

    # Manejar fecha por separado
    if alerta_update.fecha:
        alerta_existente.fecha = alerta_update.fecha

    db.commit()
    db.refresh(alerta_existente)
    return alerta_existente


@router.delete("/{alertasepp_id}", response_model=AlertasEppResponse)
def eliminar_alertasepp(alertasepp_id: int, db: Session = Depends(get_db)):
    alerta = db.query(AlertasEpp).filter(AlertasEpp.id == alertasepp_id).first()
    if not alerta:
        raise HTTPException(status_code=404, detail="AlertasEpp no encontrada.")

    # Eliminar imagen asociada si existe
    if alerta.imagen:
        try:
            image_path = Path(alerta.imagen)
            if image_path.exists():
                image_path.unlink()
        except Exception as e:
            print(f"Error eliminando imagen: {str(e)}")

    db.delete(alerta)
    db.commit()
    return alerta


@router.get("/imagen/{ruta_imagen}", response_class=FileResponse)
async def obtener_imagen_epp(ruta_imagen: str):
    """Endpoint para obtener imágenes de alertas EPP"""
    # Verificar que el nombre del archivo tenga extensión .jpg
    if not ruta_imagen.endswith('.jpg'):
        # Buscar archivos que coincidan con el UUID proporcionado
        matching_files = [f for f in os.listdir(EPP_IMAGES_DIR)
                          if f.startswith(ruta_imagen) and f.endswith('.jpg')]

        if matching_files:
            # Usar el primer archivo que coincida
            ruta_imagen = matching_files[0]
        else:
            raise HTTPException(status_code=404, detail="Imagen no encontrada")

    image_path = Path(EPP_IMAGES_DIR) / ruta_imagen
    image_path_abs = image_path.resolve()
    epp_dir_abs = Path(EPP_IMAGES_DIR).resolve()

    # Validar que la ruta esté dentro del directorio permitido
    if not image_path_abs.exists() or epp_dir_abs not in image_path_abs.parents:
        raise HTTPException(status_code=404, detail="Imagen no encontrada")

    return FileResponse(image_path_abs)