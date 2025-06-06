from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from shared.database import get_db  # Asumiendo que tienes esta función para obtener la sesión de la DB
from shared.models.productos import Productos  # Tu modelo de Productos
from servicio_general.schemas.productos_schema import ProductosCreate, ProductosResponse
from shared.schemas.paginacion import PaginatedResponse  # Los esquemas de Pydantic

router = APIRouter()


# Ruta para crear una nueva productos
@router.post("/", response_model=ProductosResponse)
def crear_productos(productos: ProductosCreate, db: Session = Depends(get_db)):
    # Verificamos si el producto con el mismo código y empresa_id ya existe
    existing_productos = db.query(Productos).filter(
        Productos.codigo == productos.codigo,
        Productos.empresa_id == productos.empresa_id
    ).first()

    if existing_productos:
        raise HTTPException(status_code=400, detail="El producto ya existe.")

    # Creamos la nueva instancia de producto
    nueva_productos = Productos(**productos.dict())
    db.add(nueva_productos)
    db.commit()
    db.refresh(nueva_productos)

    return nueva_productos


# Ruta para obtener todas las productos con paginación
@router.get("/", response_model=PaginatedResponse[ProductosResponse])
def obtener_productos(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    # Obtenemos las productos con paginación
    total_registros = db.query(Productos).count()
    productos = db.query(Productos).offset(skip).limit(limit).all()

    total_paginas = (total_registros + limit - 1) // limit  # Calculamos el total de páginas
    return PaginatedResponse(
        total_registros=total_registros,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=productos
    )


# Ruta para obtener una productos por su id
@router.get("/{codigo}/{empresa_id}", response_model=ProductosResponse)
def obtener_productos(codigo: str, empresa_id: int, db: Session = Depends(get_db)):
    producto = db.query(Productos).filter_by(codigo=codigo, empresa_id=empresa_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    return producto


# Ruta para actualizar una productos
@router.put("/{codigo}/{empresa_id}", response_model=ProductosResponse)
def actualizar_productos(codigo: str, empresa_id: int, productos: ProductosCreate, db: Session = Depends(get_db)):
    producto_existente = db.query(Productos).filter_by(codigo=codigo, empresa_id=empresa_id).first()
    if not producto_existente:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    for key, value in productos.dict().items():
        setattr(producto_existente, key, value)

    db.commit()
    db.refresh(producto_existente)
    return producto_existente



# Ruta para eliminar una productos
@router.delete("/{codigo}/{empresa_id}", response_model=ProductosResponse)
def eliminar_productos(codigo: str, empresa_id: int, db: Session = Depends(get_db)):
    producto = db.query(Productos).filter_by(codigo=codigo, empresa_id=empresa_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    db.delete(producto)
    db.commit()
    return producto
