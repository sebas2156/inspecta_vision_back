from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from Controllers.camara_controller import router as camara_router
from Controllers.cuenta_controller import router as cuenta_router
from Controllers.producto_controller import router as producto_router
from Controllers.region_controller import router as region_router
from Controllers.registro_controller import router as registro_router
from Controllers.sector_controller import router as sector_router
from database import Base, engine

app = FastAPI()

# Configurar CORS (si es necesario para tu caso)
origins = [
    "*",  # Permite todas las URLs, ajusta si necesitas restringir a ciertos dominios
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todos los encabezados
)

# Crea las tablas en la base de datos
Base.metadata.create_all(bind=engine)

# Incluir routers (con prefijos y tags descriptivos)
app.include_router(camara_router, prefix="/api/camaras", tags=["Camaras"])
app.include_router(cuenta_router, prefix="/api/cuentas", tags=["Cuentas"])
app.include_router(producto_router, prefix="/api/productos", tags=["Productos"])
app.include_router(region_router, prefix="/api/regiones", tags=["Regiones"])
app.include_router(registro_router, prefix="/api/registros", tags=["Registros"])
app.include_router(sector_router, prefix="/api/sectores", tags=["Sectores"])
