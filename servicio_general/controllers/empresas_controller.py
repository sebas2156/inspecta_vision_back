from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models.empresas import Empresas
from servicio_general.schemas.empresas_schema import EmpresasCreate, EmpresasResponse
from shared.schemas.paginacion import PaginatedResponse

router = APIRouter()

@router.post("/", response_model=EmpresasResponse)
def crear_empresa(empresa: EmpresasCreate, db: Session = Depends(get_db)):
    nueva_empresa = Empresas(**empresa.dict())
    db.add(nueva_empresa)
    db.commit()
    db.refresh(nueva_empresa)
    return nueva_empresa

@router.get("/", response_model=PaginatedResponse[EmpresasResponse])
def obtener_empresas(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    total_registros = db.query(Empresas).count()
    empresas = db.query(Empresas).offset(skip).limit(limit).all()
    total_paginas = (total_registros + limit - 1) // limit
    return PaginatedResponse(
        total_registros=total_registros,
        por_pagina=limit,
        pagina_actual=skip // limit + 1,
        total_paginas=total_paginas,
        data=empresas
    )

@router.get("/{empresa_id}", response_model=EmpresasResponse)
def obtener_empresa(empresa_id: int, db: Session = Depends(get_db)):
    empresa = db.query(Empresas).filter(Empresas.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada.")
    return empresa


@router.put("/{empresa_id}", response_model=EmpresasResponse)
def actualizar_empresa(empresa_id: int, empresa: EmpresasCreate, db: Session = Depends(get_db)):
    # Verificamos si la empresa existe
    empresa_existente = db.query(Empresas).filter(Empresas.id == empresa_id).first()
    if not empresa_existente:
        raise HTTPException(status_code=404, detail="Empresa no encontrada.")

    # Actualizamos los campos de la empresa de manera más eficiente
    for key, value in empresa.dict().items():
        setattr(empresa_existente, key, value)

    # Guardamos los cambios en la base de datos
    db.commit()
    db.refresh(empresa_existente)

    return empresa_existente

@router.delete("/{empresa_id}", response_model=EmpresasResponse)
def eliminar_empresa(empresa_id: int, db: Session = Depends(get_db)):
    empresa = db.query(Empresas).filter(Empresas.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada.")
    db.delete(empresa)
    db.commit()
    return empresa