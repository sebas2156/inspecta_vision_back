from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configuración de la URL de conexión a la base de datos
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root@localhost/prueba6"  # Cambia esto según tu base de datos

# Crear el motor de SQLAlchemy
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"charset": "utf8mb4"}  # Esto es importante si usas MySQL/MariaDB para la codificación de caracteres
)

# Crear la clase base para todos los modelos
Base = declarative_base()

# Crear la clase SessionLocal para manejar las sesiones de la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependencia para obtener la sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
