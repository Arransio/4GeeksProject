"""Entrypoint ASGI de la imagen Docker de /services.

Cablea catalogs + IncidentService + FastAPI en un objeto `app` de nivel modulo
para que Uvicorn pueda arrancarlo con --reload y recargarlo en cada cambio.
"""

import os

from services.incident_manager.api import create_app, load_catalogs
from services.incident_manager.service import IncidentService

CATALOGS_FILE = os.environ.get(
    "INCIDENT_CATALOGS_FILE",
    "/app/services/incident_manager/catalogs.json",
)
# Base de datos fuera de /app: esta en el cwd y no debe disparar el reloader.
DATABASE_PATH = os.environ.get("INCIDENT_DATABASE", "/tmp/incident-manager.sqlite3")
# Directorio de estaticos (backoffice). Si no se copia el de uis, se crea vacio
# para que StaticFiles no falle al montar el mount.
STATIC_DIR = os.environ.get("INCIDENT_STATIC_DIR", "/app/static")

os.makedirs(STATIC_DIR, exist_ok=True)

_service = IncidentService(DATABASE_PATH, load_catalogs(CATALOGS_FILE))
app = create_app(_service, static_dir=STATIC_DIR)