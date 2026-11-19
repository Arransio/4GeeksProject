"""Run the incident manager locally with operator-provided catalogs."""

import os

import uvicorn

from services.incident_manager.api import create_app, load_catalogs
from services.incident_manager.service import IncidentService


def main() -> None:
    catalogs_path = os.environ.get(
        "INCIDENT_CATALOGS_FILE",
        str(os.path.join(os.path.dirname(__file__), "catalogs.json")),
    )
    database_path = os.environ.get("INCIDENT_DATABASE", "incident-manager.sqlite3")
    host = os.environ.get("INCIDENT_HOST", "127.0.0.1")
    port = int(os.environ.get("INCIDENT_PORT", "8000"))
    service = IncidentService(database_path, load_catalogs(catalogs_path))
    app = create_app(service)
    try:
        uvicorn.run(app, host=host, port=port)
    finally:
        service.close()


if __name__ == "__main__":
    main()