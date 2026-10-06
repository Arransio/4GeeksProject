"""Run the incident manager locally with operator-provided catalogs."""

import os
from wsgiref.simple_server import make_server

from services.incident_manager.api import create_app, load_catalogs
from services.incident_manager.service import IncidentService


def main() -> None:
    catalogs_path = os.environ.get("INCIDENT_CATALOGS_FILE")
    if not catalogs_path:
        raise SystemExit("Set INCIDENT_CATALOGS_FILE to an approved catalog JSON file")
    database_path = os.environ.get("INCIDENT_DATABASE", "incident-manager.sqlite3")
    host = os.environ.get("INCIDENT_HOST", "127.0.0.1")
    port = int(os.environ.get("INCIDENT_PORT", "8000"))
    service = IncidentService(database_path, load_catalogs(catalogs_path))
    app = create_app(service)
    try:
        with make_server(host, port, app) as server:
            print(f"Incident manager listening on http://{host}:{port}")
            server.serve_forever()
    finally:
        service.close()


if __name__ == "__main__":
    main()