# Gestor de incidencias

API FastAPI, persistencia SQLite y backoffice estático para centralizar las incidencias de operación de HealthCore.

## Funcionalidad

- Crear, editar, listar y consultar incidencias.
- Asignar un área responsable y recorrer transiciones declaradas en el catálogo.
- Registrar en una tabla append-only quién creó o modificó cada campo, el valor anterior/nuevo y la marca temporal UTC.
- Filtrar por estado, severidad y área responsable.
- Contar incidencias abiertas por severidad; el catálogo declara explícitamente cuáles son estados cerrados.
- Servir la interfaz ubicada en `uis/backoffice/incidents/`.

## Catálogos

Los catálogos aprobados para HealthCore están en [`catalogs.json`](./catalogs.json). Se pueden sustituir en otro entorno mediante `INCIDENT_CATALOGS_FILE`. Para la trazabilidad solicitada, el actor declarado se recibe en `X-Actor` y el panel permite introducirlo.

## Instalar y ejecutar

Desde la raíz del repositorio, con Python 3.7 o posterior, instala las dependencias del servicio y arráncalo con Uvicorn:

```bash
python3 -m pip install -r services/incident_manager/requirements.txt
INCIDENT_DATABASE=incident-manager.sqlite3 \
PYTHONPATH=. python3 -m services.incident_manager
```

Variables opcionales: `INCIDENT_CATALOGS_FILE` (por defecto `catalogs.json` del servicio), `INCIDENT_HOST` (por defecto `127.0.0.1`) e `INCIDENT_PORT` (por defecto `8000`). Abre `http://127.0.0.1:8000/`.

## API

- `GET /api/catalogs`
- `GET /api/incidents?status=...&severity=...&responsible_area=...`
- `POST /api/incidents`
- `GET /api/incidents/{incident_id}`
- `PATCH /api/incidents/{incident_id}` para editar campos, asignar un área o cambiar estado (operaciones separadas)
- `GET /api/incidents/{incident_id}/history`
- `GET /api/summary/open-by-severity`

Las escrituras requieren `X-Actor`; su valor se registra como autor declarado de la operación.

## Pruebas

Desde la raíz del repositorio:

```bash
python3 -m pip install -r services/incident_manager/requirements-dev.txt
PYTHONPATH=. python3 -m unittest services.incident_manager.test_service services.incident_manager.test_api -v
```
