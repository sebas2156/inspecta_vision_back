from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from shared.database import get_db  # Asumiendo que tienes esta función para obtener la sesión de la DB
from shared.models.productosector import ProductoSector  # Tu modelo de ProductoSector
from servicio_general.schemas.productosector_schema import ProductoSectorCreate, ProductoSectorResponse
from shared.schemas.paginacion import PaginatedResponse  # Los esquemas de Pydantic

router = APIRouter()


# Ruta para crear una nueva productosector
@router.post("/", response_model=ProductoSectorResponse)
def crear_productosector(productosector: ProductoSectorCreate, db: Session = Depends(get_db)):
    # Verificamos si la productosector con el mismo correo ya existe
    existing_productosector = db.query(ProductoSector).filter(ProductoSector.correo == productosector.correo).first()
    if existing_productosector:
        raise HTTPException(status_code=400, detail="La productosector ya existe.")

    # Creamos la nueva productosector
    nueva_productosector = ProductoSector(**productosector.dict())
    db.add(nueva_productosector)
    db.commit()
    db.refresh(nueva_productosector)
    return nueva_productosector


# Ruta para obtener todas las productosector con paginación
@router.get("/", response_model=PaginatedResponse[ProductoSectorResponse])
def obtener_productosector(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    # Obtenemos las productosector con paginación
    total_registros = db.query(ProductoSector).count()
    productosector = db.query(ProductoSector).offset(skip).limit(limit).all()

    total_paginas = (total_registros + limit - 1) // limit  # Calculamos el total de páginas
    return PaginatedResponse(
        total_registros=total_registros,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=productosector
    )


# Ruta para obtener una productosector por su id
@router.get("/{productosector_id}", response_model=ProductoSectorResponse)
def obtener_productosector(productosector_id: int, db: Session = Depends(get_db)):
    productosector = db.query(ProductoSector).filter(ProductoSector.id == productosector_id).first()
    if not productosector:
        raise HTTPException(status_code=404, detail="ProductoSector no encontrada.")
    return productosector


# Ruta para actualizar una productosector
@router.put("/{productosector_id}", response_model=ProductoSectorResponse, tags=["ProductoSector"])
def actualizar_productosector(productosector_id: int, productosector: ProductoSectorCreate, db: Session = Depends(get_db)):
    # Verificamos si la cuenta existe
    productosector_existente = db.query(ProductoSector).filter(ProductoSector.id == productosector_id).first()
    if not productosector_existente:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

    # Actualizamos los campos de la cuenta de manera más eficiente
    for key, value in productosector.dict().items():
        setattr(productosector_existente, key, value)

    # Guardamos los cambios en la base de datos
    db.commit()
    db.refresh(productosector_existente)

    return productosector_existente


# Ruta para eliminar una productosector
@router.delete("/{productosector_id}", response_model=ProductoSectorResponse)
def eliminar_productosector(productosector_id: int, db: Session = Depends(get_db)):
    productosector = db.query(ProductoSector).filter(ProductoSector.id == productosector_id).first()
    if not productosector:
        raise HTTPException(status_code=404, detail="ProductoSector no encontrada.")

    db.delete(productosector)
    db.commit()
    return productosector