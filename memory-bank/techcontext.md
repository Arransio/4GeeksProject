# Contexto tecnico del repositorio

## Estructura observada

- `services/` es la ubicacion documentada para APIs y workers de compania; cada servicio debe tener su propia documentacion.
- `uis/` contiene las interfaces de usuario y documenta `uis/backoffice/` como ubicacion para la aplicacion interna.
- `docs/` contiene documentacion transversal.
- `inventoryManager/` es un ejemplo independiente existente en la raiz, no una API central de la compania.

## Stack y pruebas comprobados

- El ejemplo `inventoryManager/` usa Python, WSGI y SQLite. Su servicio de dominio es en memoria; el esquema SQL existe aparte y el README advierte que ambos aun no estan conectados.
- Los tests de Python usan `unittest`; el README del ejemplo indica `python -m unittest discover -s . -v` desde `inventoryManager/`.
- No se encontro un manifiesto de dependencias o un runner de aplicacion en la raiz. El post-create del devcontainer invoca `uv sync`, pero no hay `pyproject.toml` en el checkout.
- Los README del monorepo describen una API central FastAPI, pero no hay un servicio implementado bajo `services/` que establezca ese patron en codigo.

## Convenciones

- Python: `snake_case` para modulos, funciones, metodos y variables; `PascalCase` para clases.
- SQL: nombres `snake_case`; los movimientos del ejemplo de inventario son append-only y las restricciones criticas se prueban.
- Mantener el backend y la interfaz en sus areas documentadas, evitar dependencias nuevas sin justificar y ejecutar pruebas automatizadas del slice modificado.

## Runtime del gestor de incidencias

El gestor sigue FastAPI, como recomienda el README del monorepo. Uvicorn sirve la API y el backoffice estático; las versiones están fijadas en `services/incident_manager/requirements.txt` para mantener compatibilidad con Python 3.7 disponible en el entorno de trabajo. `httpx` está separado en `requirements-dev.txt` para ejecutar `TestClient`.

## Capa de aplicacion: donde vive cada app cuando se cree

Este hito no crea apps de producto. Cuando se creen, van en las carpetas que ya mapea la plantilla; no se inventa un arbol paralelo de frontend ni de API en otro sitio. Antes de poner nada en cada ruta, se lee su README local.

| Ruta | Que va ahi |
| --- | --- |
| `uis/website/` | Proyecto frontend publico de HealthCore: web corporativa de cara al publico (ruta `/`), marca y copy alineados con `CONTEXT.md`. Todavia no existe. |
| `uis/backoffice/` | App interna de la empresa (layout propio, separada del sitio publico; vista de entrada en `/`). Aqui ya viven `incidents/` e `inventory/`. |
| `services/` | APIs y workers backend. Aqui ya vive `incident_manager/`; las APIs nuevas de HealthCore se anaden a este arbol. |

Regla derivada: el backoffice nuevo se anade como subcarpeta de `uis/backoffice/` y su backend en `services/`; nunca se crea `frontend/`, `app/` o `api/` en la raiz como arbol paralelo.
