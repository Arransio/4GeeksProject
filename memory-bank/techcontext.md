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
