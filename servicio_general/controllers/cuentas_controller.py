from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from shared.database import get_db  # Asumiendo que tienes esta función para obtener la sesión de la DB
from shared.models.cuentas import Cuentas  # Tu modelo de Cuentas
from servicio_general.schemas.cuentas_schema import CuentasCreate, CuentasResponse, LoginRequest, LoginResponse
from shared.schemas.paginacion import PaginatedResponse  # Los esquemas de Pydantic

router = APIRouter()


# Ruta para crear una nueva cuentas
@router.post("/", response_model=CuentasResponse)
def crear_cuentas(cuentas: CuentasCreate, db: Session = Depends(get_db)):
    # Verificamos si la cuentas con el mismo correo ya existe
    existing_cuentas = db.query(Cuentas).filter(Cuentas.correo == cuentas.correo).first()
    if existing_cuentas:
        raise HTTPException(status_code=400, detail="La cuentas con ese correo ya existe.")

    # Creamos la nueva cuentas
    nueva_cuentas = Cuentas(**cuentas.dict())
    db.add(nueva_cuentas)
    db.commit()
    db.refresh(nueva_cuentas)
    return nueva_cuentas


# Ruta para obtener todas las cuentas con paginación
@router.get("/", response_model=PaginatedResponse[CuentasResponse])
def obtener_cuentas(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    # Obtenemos las cuentas con paginación
    total_registros = db.query(Cuentas).count()
    cuentas = db.query(Cuentas).offset(skip).limit(limit).all()

    total_paginas = (total_registros + limit - 1) // limit  # Calculamos el total de páginas
    return PaginatedResponse(
        total_registros=total_registros,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=cuentas
    )


# Ruta para obtener una cuentas por su id
@router.get("/{cuentas_id}", response_model=CuentasResponse)
def obtener_cuentas(cuentas_id: int, db: Session = Depends(get_db)):
    cuentas = db.query(Cuentas).filter(Cuentas.id == cuentas_id).first()
    if not cuentas:
        raise HTTPException(status_code=404, detail="Cuentas no encontrada.")
    return cuentas


# Ruta para actualizar una cuentas
@router.put("/{cuentas_id}", response_model=CuentasResponse, tags=["Cuentas"])
def actualizar_cuentas(cuentas_id: int, cuentas: CuentasCreate, db: Session = Depends(get_db)):
    # Verificamos si la cuenta existe
    cuentas_existente = db.query(Cuentas).filter(Cuentas.id == cuentas_id).first()
    if not cuentas_existente:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

    # Actualizamos los campos de la cuenta de manera más eficiente
    for key, value in cuentas.dict().items():
        setattr(cuentas_existente, key, value)

    # Guardamos los cambios en la base de datos
    db.commit()
    db.refresh(cuentas_existente)

    return cuentas_existente


# Ruta para eliminar una cuentas
@router.delete("/{cuentas_id}", response_model=CuentasResponse)
def eliminar_cuentas(cuentas_id: int, db: Session = Depends(get_db)):
    cuentas = db.query(Cuentas).filter(Cuentas.id == cuentas_id).first()
    if not cuentas:
        raise HTTPException(status_code=404, detail="Cuentas no encontrada.")

    db.delete(cuentas)
    db.commit()
    return cuentas


# Ruta para login
@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Autenticación de usuario",
    description="Verifica las credenciales y devuelve información básica del usuario",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Autenticación exitosa"},
        401: {"description": "Credenciales inválidas"},
        404: {"description": "Usuario no encontrado"}
    }
)
def login(login_request: LoginRequest, db: Session = Depends(get_db)):
    # Buscar usuario por email
    cuenta = db.query(Cuentas).filter(Cuentas.email == login_request.email).first()

    if not cuenta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verificar contraseña (en texto plano por ahora - mejorar para producción)
    if cuenta.contraseña != login_request.contraseña:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña incorrecta",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Si todo es correcto, devolver la respuesta
    return LoginResponse(
        nombre=cuenta.nombre,
        rol=cuenta.rol
    )