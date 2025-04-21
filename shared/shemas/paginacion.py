from pydantic import BaseModel
from typing import List, TypeVar, Generic

T = TypeVar('T')  # Define un tipo genérico

class PaginatedResponse(BaseModel, Generic[T]):
    total_registros: int
    por_pagina: int
    pagina_actual: int
    total_paginas: int
    data: List[T]  # La lista es del tipo T, que puede ser cualquier tipo de objeto específico
