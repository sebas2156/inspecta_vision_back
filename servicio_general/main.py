from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from servicio_general.controllers.camaras_controller import router as camara_router
from servicio_general.controllers.cuentas_controller import router as cuenta_router
from servicio_general.controllers.regiones_controller import router as region_router
from servicio_general.controllers.sectores_controller import router as sector_router
from servicio_general.controllers.empresas_controller import router as empresa_router
from servicio_general.controllers.servicios_controller import router as servicios_router
from servicio_general.controllers.logs_controller import router as logs_router
from servicio_general.controllers.suscripciones_controller import router as suscripciones_router
from servicio_general.controllers.modelosia_controller import router as modelosia_router
from servicio_general.controllers.reglasepp_controller import router as reglasepp_router
from servicio_general.controllers.alertasepp_controller import router as alertasepp_router
from servicio_general.controllers.productos_controller import router as productos_router
from servicio_general.controllers.alertasiventario_controller import router as alertasiventario_router
from servicio_general.controllers.registroinventario_controller import router as registroinventario_router
from servicio_general.controllers.productosector_controller import router as productosector_router


from shared.database import Base, engine

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
app.include_router(region_router, prefix="/api/regiones", tags=["Regiones"])
app.include_router(sector_router, prefix="/api/sectores", tags=["Sectores"])
app.include_router(logs_router, prefix="/api/logs", tags=["Logs"])
app.include_router(suscripciones_router, prefix="/api/suscripciones", tags=["Suscripciones"])
app.include_router(empresa_router, prefix="/api/empresas", tags=["Empresas"])
app.include_router(servicios_router, prefix="/api/servicios", tags=["Servicios"])
app.include_router(modelosia_router, prefix="/api/modelosia", tags=["Modelosia"])
app.include_router(reglasepp_router, prefix="/api/reglasepp", tags=["Reglas EPP"])
app.include_router(alertasepp_router, prefix="/api/alertasepp", tags=["Alertas EPP"])
app.include_router(productos_router, prefix="/api/productos", tags=["Productos"])
app.include_router(alertasiventario_router, prefix="/api/alertasiventario", tags=["Alertas Iventario"])
app.include_router(registroinventario_router, prefix="/api/registroinventario", tags=["Registro Inventario"])
app.include_router(productosector_router, prefix="/api/productosector", tags=["Productos por Sector"])
