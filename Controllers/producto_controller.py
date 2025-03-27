from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db  # Asumiendo que tienes esta función para obtener la sesión de la DB
from Models.producto import Producto  # Tu modelo de Producto
from Schemas.producto_schema import ProductoCreate, ProductoResponse, PaginatedProductoResponse  # Los esquemas de Pydantic

router = APIRouter()


# Ruta para crear un nuevo producto
@router.post("/", response_model=ProductoResponse)
def crear_producto(producto: ProductoCreate, db: Session = Depends(get_db)):
    # Verificamos si el producto ya existe por código
    existing_producto = db.query(Producto).filter(Producto.codigo == producto.codigo).first()
    if existing_producto:
        raise HTTPException(status_code=400, detail="El producto con ese código ya existe.")

    # Creamos el nuevo producto
    nuevo_producto = Producto(
        codigo=producto.codigo,
        nombre_producto=producto.nombre_producto,
        descripcion=producto.descripcion,
        caducidad=producto.caducidad,
        stock=producto.stock,
        sector=producto.sector
    )
    db.add(nuevo_producto)
    db.commit()
    db.refresh(nuevo_producto)
    return nuevo_producto


# Ruta para obtener todos los productos con paginación
@router.get("/", response_model=PaginatedProductoResponse)
def obtener_productos(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    # Obtenemos los productos con paginación
    total_registros = db.query(Producto).count()
    productos = db.query(Producto).offset(skip).limit(limit).all()

    total_paginas = (total_registros + limit - 1) // limit  # Calculamos el total de páginas
    return PaginatedProductoResponse(
        total_registros=total_registros,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=productos
    )


# Ruta para obtener un producto por su código
@router.get("/{producto_codigo}", response_model=ProductoResponse)
def obtener_producto(producto_codigo: str, db: Session = Depends(get_db)):
    producto = db.query(Producto).filter(Producto.codigo == producto_codigo).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    return producto


# Ruta para actualizar un producto
@router.put("/{producto_codigo}", response_model=ProductoResponse)
def actualizar_producto(producto_codigo: str, producto: ProductoCreate, db: Session = Depends(get_db)):
    producto_existente = db.query(Producto).filter(Producto.codigo == producto_codigo).first()
    if not producto_existente:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    # Actualizamos los valores del producto
    producto_existente.codigo = producto.codigo
    producto_existente.nombre_producto = producto.nombre_producto
    producto_existente.descripcion = producto.descripcion
    producto_existente.categoria = producto.categoria
    producto_existente.stock = producto.stock
    producto_existente.sector = producto.sector
    db.commit()
    db.refresh(producto_existente)
    return producto_existente


# Ruta para eliminar un producto
@router.delete("/{producto_codigo}", response_model=ProductoResponse)
def eliminar_producto(producto_codigo: str, db: Session = Depends(get_db)):
    producto = db.query(Producto).filter(Producto.codigo == producto_codigo).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    db.delete(producto)
    db.commit()
    return producto
