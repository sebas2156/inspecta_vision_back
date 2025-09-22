from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, select
from shared.database import get_db  # Asumiendo que tienes esta función para obtener la sesión de la DB
from shared.models.registrosinventario import RegistrosInventario  # Tu modelo de RegistrosInventario
from shared.models.productosector import ProductoSector
from servicio_general.schemas.registrosinventario_schema import RegistrosInventarioCreate, RegistrosInventarioResponse
from shared.schemas.paginacion import PaginatedResponse  # Los esquemas de Pydantic
from datetime import timedelta, datetime
from sqlalchemy.exc import IntegrityError
import threading
import time

router = APIRouter()

# 1. Sistema de caché con expiración
prediction_cache = {}
cache_lock = threading.Lock()
CACHE_TIMEOUT = 3600  # 1 hora en segundos

from datetime import datetime, timedelta
import pandas as pd
from prophet import Prophet
from fastapi import HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from fastapi import HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import random
# Modelos Pydantic
class PrediccionResponse(BaseModel):
    fecha: str
    cantidad: float

class PrediccionListResponse(BaseModel):
    prediccion: List[PrediccionResponse]


def generar_prediccion_con_promedio(resultados: list, dias_prediccion: int):
    """Predicción basada en promedio histórico"""
    if resultados:
        # Calcular promedio de todos los datos
        promedio = sum(r.cantidad for r in resultados) / len(resultados)
    else:
        # Valor por defecto más realista (ajustar según necesidades)
        promedio = random.uniform(2.0, 5.0)

    hoy = datetime.now().date()
    predicciones = []
    for i in range(1, dias_prediccion + 1):
        fecha = (hoy + timedelta(days=i)).strftime('%Y-%m-%d')
        predicciones.append(PrediccionResponse(
            fecha=fecha,
            cantidad=round(promedio, 2)
        ))
    return predicciones


def generar_prediccion_promedio_movil(resultados: list, dias_prediccion: int, ventana: int = 7):
    """Predicción basada en promedio móvil"""
    if not resultados:
        return generar_prediccion_con_promedio([], dias_prediccion)

    # Obtener las últimas N cantidades
    ultimos_valores = [r.cantidad for r in resultados[-ventana:]]
    promedio = sum(ultimos_valores) / len(ultimos_valores)

    hoy = datetime.now().date()
    predicciones = []
    for i in range(1, dias_prediccion + 1):
        fecha = (hoy + timedelta(days=i)).strftime('%Y-%m-%d')
        predicciones.append(PrediccionResponse(
            fecha=fecha,
            cantidad=round(promedio, 2)
        ))
    return predicciones


def generar_prediccion_valor_constante(resultados: list, dias_prediccion: int):
    """Predicción usando el último valor conocido"""
    if resultados:
        valor = resultados[-1].cantidad
    else:
        valor = random.uniform(2.0, 5.0)  # Valor por defecto

    hoy = datetime.now().date()
    predicciones = []
    for i in range(1, dias_prediccion + 1):
        fecha = (hoy + timedelta(days=i)).strftime('%Y-%m-%d')
        predicciones.append(PrediccionResponse(
            fecha=fecha,
            cantidad=round(valor, 2)
        ))
    return predicciones


def generar_prediccion_lineal(resultados: list, dias_prediccion: int):
    """Predicción usando regresión lineal"""
    # 1. Preparar datos para regresión lineal
    fechas = [r.fecha for r in resultados]
    dias_desde_inicio = [(fecha - min(fechas)).days for fecha in fechas]

    X = np.array(dias_desde_inicio).reshape(-1, 1)
    y = np.array([r.cantidad for r in resultados])

    # 2. Crear y entrenar modelo
    modelo = LinearRegression()
    modelo.fit(X, y)

    # 3. Generar predicciones para días futuros
    ultimo_dia = max(dias_desde_inicio)
    dias_futuros = [ultimo_dia + i for i in range(1, dias_prediccion + 1)]
    X_futuro = np.array(dias_futuros).reshape(-1, 1)
    y_pred = modelo.predict(X_futuro)

    # 4. Generar fechas futuras
    ultima_fecha = max(fechas)
    fechas_futuras = [ultima_fecha + timedelta(days=i) for i in range(1, dias_prediccion + 1)]

    # 5. Formatear respuesta
    predicciones = []
    for fecha, cantidad in zip(fechas_futuras, y_pred):
        predicciones.append(PrediccionResponse(
            fecha=fecha.strftime('%Y-%m-%d'),
            cantidad=max(0, round(float(cantidad), 2)  # Evitar valores negativos
                         )))

    return predicciones


@router.get("/prediccion/demanda", response_model=PrediccionListResponse)
async def obtener_prediccion_demanda(
        producto_codigo: str = Query(..., title="Código del producto"),
        empresa_id: int = Query(..., title="ID de la empresa"),
        dias_prediccion: int = Query(7, title="Días a predecir"),
        db: Session = Depends(get_db)
):
    # 2. Clave única para la caché
    cache_key = (producto_codigo, empresa_id, dias_prediccion)

    # 3. Verificar si existe en caché
    with cache_lock:
        cache_entry = prediction_cache.get(cache_key)
        if cache_entry:
            timestamp, response = cache_entry
            if time.time() - timestamp < CACHE_TIMEOUT:
                return response

    try:
        # 4. Lógica de predicción (original)
        fecha_limite = datetime.now() - timedelta(days=730)
        resultados = db.query(
            func.date(RegistrosInventario.fecha).label("fecha"),
            func.count().label("cantidad")
        ).filter(
            func.trim(RegistrosInventario.producto_codigo) == producto_codigo.strip(),
            RegistrosInventario.empresa_id == empresa_id,
            func.lower(func.trim(RegistrosInventario.accion)) == 'salio',
            RegistrosInventario.fecha >= fecha_limite
        ).group_by(func.date(RegistrosInventario.fecha)) \
            .order_by(func.date(RegistrosInventario.fecha)) \
            .all()

        if not resultados:
            predicciones = generar_prediccion_valor_constante([], dias_prediccion)
        else:
            n = len(resultados)
            if n < 5:
                predicciones = generar_prediccion_valor_constante(resultados, dias_prediccion)
            elif n < 10:
                predicciones = generar_prediccion_con_promedio(resultados, dias_prediccion)
            elif n < 20:
                predicciones = generar_prediccion_promedio_movil(resultados, dias_prediccion, ventana=7)
            else:
                predicciones = generar_prediccion_lineal(resultados, dias_prediccion)

        response = PrediccionListResponse(prediccion=predicciones)

        # 5. Almacenar en caché
        with cache_lock:
            prediction_cache[cache_key] = (time.time(), response)

        return response

    except Exception as e:
        # Manejo de errores (sin almacenar en caché)
        predicciones = generar_prediccion_valor_constante([], dias_prediccion)
        return PrediccionListResponse(prediccion=predicciones)

# Ruta para crear una nueva registrosinventario
@router.post("/", response_model=RegistrosInventarioResponse)
def crear_registrosinventario(
    registrosinventario: RegistrosInventarioCreate,
    db: Session = Depends(get_db)
):
    try:
        # Crear el nuevo registro
        nueva_registrosinventario = RegistrosInventario(**registrosinventario.dict())
        db.add(nueva_registrosinventario)

        # Intentar actualizar el stock del producto en el sector
        producto_sector = db.query(ProductoSector).filter(
            ProductoSector.producto_codigo == registrosinventario.producto_codigo,
            ProductoSector.sector_id == registrosinventario.sector_id,
            ProductoSector.empresa_id == registrosinventario.empresa_id
        ).first()

        if producto_sector:
            if registrosinventario.accion == "salio":
                producto_sector.stock = max(0, producto_sector.stock - 1)
            elif registrosinventario.accion == "entro":
                producto_sector.stock += 1
        else:
            # Crear nuevo registro en producto_sector
            stock_inicial = 1 if registrosinventario.accion == "entro" else 0
            producto_sector = ProductoSector(
                producto_codigo=registrosinventario.producto_codigo,
                sector_id=registrosinventario.sector_id,
                empresa_id=registrosinventario.empresa_id,
                stock=stock_inicial,
                permitido=True
            )
            db.add(producto_sector)

        db.commit()
        db.refresh(nueva_registrosinventario)
        return nueva_registrosinventario

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Error de integridad. Verifica que el producto exista y los datos sean válidos."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ocurrió un error al crear el registro: {str(e)}"
        )


# Ruta para obtener todas las registrosinventario con paginación
@router.get("/", response_model=PaginatedResponse[RegistrosInventarioResponse])
def obtener_registrosinventario(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    # Obtenemos las registrosinventario con paginación
    total_registros = db.query(RegistrosInventario).count()
    registrosinventario = db.query(RegistrosInventario).offset(skip).limit(limit).all()

    total_paginas = (total_registros + limit - 1) // limit  # Calculamos el total de páginas
    return PaginatedResponse(
        total_registros=total_registros,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=registrosinventario
    )


# Ruta para obtener una registrosinventario por su id
@router.get("/{registrosinventario_id}", response_model=RegistrosInventarioResponse)
def obtener_registrosinventario(registrosinventario_id: int, db: Session = Depends(get_db)):
    registrosinventario = db.query(RegistrosInventario).filter(RegistrosInventario.id == registrosinventario_id).first()
    if not registrosinventario:
        raise HTTPException(status_code=404, detail="RegistrosInventario no encontrada.")
    return registrosinventario


# Ruta para actualizar una registrosinventario
@router.put("/{registrosinventario_id}", response_model=RegistrosInventarioResponse, tags=["RegistrosInventario"])
def actualizar_registrosinventario(registrosinventario_id: int, registrosinventario: RegistrosInventarioCreate, db: Session = Depends(get_db)):
    # Verificamos si la cuenta existe
    registrosinventario_existente = db.query(RegistrosInventario).filter(RegistrosInventario.id == registrosinventario_id).first()
    if not registrosinventario_existente:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

    # Actualizamos los campos de la cuenta de manera más eficiente
    for key, value in registrosinventario.dict().items():
        setattr(registrosinventario_existente, key, value)

    # Guardamos los cambios en la base de datos
    db.commit()
    db.refresh(registrosinventario_existente)

    return registrosinventario_existente


# Ruta para eliminar una registrosinventario
@router.delete("/{registrosinventario_id}", response_model=RegistrosInventarioResponse)
def eliminar_registrosinventario(registrosinventario_id: int, db: Session = Depends(get_db)):
    registrosinventario = db.query(RegistrosInventario).filter(RegistrosInventario.id == registrosinventario_id).first()
    if not registrosinventario:
        raise HTTPException(status_code=404, detail="RegistrosInventario no encontrada.")

    db.delete(registrosinventario)
    db.commit()
    return registrosinventario



