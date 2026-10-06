# Gestor de incidencias

Servicio WSGI, SQLite y backoffice estático para centralizar las incidencias de operación de HealthCore.

## Funcionalidad

- Crear, editar, listar y consultar incidencias.
- Asignar un área responsable y recorrer transiciones declaradas en el catálogo.
- Registrar en una tabla append-only quién creó o modificó cada campo, el valor anterior/nuevo y la marca temporal UTC.
- Filtrar por estado, severidad y área responsable.
- Contar incidencias abiertas por severidad; el catálogo declara explícitamente cuáles son estados cerrados.
- Servir la interfaz ubicada en `uis/backoffice/incidents/`.

## Catálogos requeridos

No se incluyen valores de tipo, severidad, canal ni transición en el repositorio: el briefing de empresa compartido no los especifica. El servicio se niega a arrancar sin un archivo JSON aprobado mediante `INCIDENT_CATALOGS_FILE`. El archivo debe tener esta forma; los valores siguientes son marcadores estructurales, no catálogos de HealthCore:

```json
{
  "incident_types": ["<tipo aprobado>"],
  "severities": ["<severidad aprobada>"],
  "channels": ["<canal aprobado>"],
  "areas": ["Operaciones Clínicas", "Experiencia del Paciente y Acceso", "Ciclo de Ingresos y Facturación", "Cumplimiento y Gobierno del Dato", "Personas y Fuerza Laboral", "Tecnología", "Dirección Ejecutiva"],
  "statuses": ["<estado inicial>", "<estado final>"],
  "closed_statuses": ["<estado final>"],
  "initial_status": "<estado inicial>",
  "transitions": {"<estado inicial>": ["<estado final>"]}
}
```

Las áreas deben coincidir con el briefing de HealthCore. La autenticación corporativa no está implementada: el actor se recibe en `X-Actor` y el panel usa el correo introducido por el operador. No desplegar ni exponer el servicio sin integrar un proveedor de identidad y autorización.

## Ejecutar

Desde la raíz del repositorio, con Python 3.7 o posterior:

```bash
INCIDENT_CATALOGS_FILE=/ruta/a/catalogos-aprobados.json \
INCIDENT_DATABASE=incident-manager.sqlite3 \
PYTHONPATH=. python3 -m services.incident_manager
```

Variables opcionales: `INCIDENT_HOST` (por defecto `127.0.0.1`) e `INCIDENT_PORT` (por defecto `8000`). Abre `http://127.0.0.1:8000/`.

## API

- `GET /api/catalogs`
- `GET /api/incidents?status=...&severity=...&responsible_area=...`
- `POST /api/incidents`
- `GET /api/incidents/{incident_id}`
- `PATCH /api/incidents/{incident_id}` para editar campos, asignar un área o cambiar estado (operaciones separadas)
- `GET /api/incidents/{incident_id}/history`
- `GET /api/summary/open-by-severity`

Las escrituras requieren `X-Actor`. La API no maneja credenciales ni datos clínicos; no enviar identificadores directos ni información de salud en título o descripción.

## Pruebas

Desde la raíz del repositorio:

```bash
PYTHONPATH=. python3 -m unittest services.incident_manager.test_service services.incident_manager.test_api -v
```
