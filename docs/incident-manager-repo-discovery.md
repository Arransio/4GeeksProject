# Reconocimiento del repositorio para el gestor de incidencias

## Resumen preliminar

El repositorio es un monorepo empresarial con areas separadas para interfaces (`uis/`), servicios (`services/`), datos, agentes, automatizacion, infraestructura y documentacion. El README recomienda una API central FastAPI y ubica el backoffice bajo `uis/backoffice/`.

## Contraste con el checkout

| Hipotesis del resumen | Evidencia observada | Resultado |
| --- | --- | --- |
| Hay una API central implementada en `services/`. | `services/README.md` describe donde deben vivir los servicios, pero no hay codigo de servicio en esa carpeta. | La estructura esta preparada; la API aun no existe. |
| FastAPI es un patron ejecutable del repo. | El README lo recomienda, pero el ejemplo ejecutable `inventoryManager/api.py` usa WSGI de la biblioteca estandar. | Hay una discrepancia entre la recomendacion y el codigo existente. |
| El ejemplo de inventario usa persistencia SQLite conectada al backend. | `inventoryManager/README.md` indica que el servicio de dominio es en memoria y que el esquema SQLite no esta conectado a la API. | Solo hay un esquema SQL separado, no persistencia integrada. |
| Existe una configuracion de dependencias en la raiz. | No hay `pyproject.toml`, `uv.lock`, `package.json`, `requirements*.txt` ni `docker-compose.yml` en la raiz inspeccionada. `.devcontainer/post-create.sh` ejecuta `uv sync`. | La configuracion de desarrollo esta incompleta o depende de archivos ausentes. |
| Hay un ejemplo de pruebas reutilizable. | `inventoryManager/test_inventory.py` usa `unittest`; el README documenta su comando de descubrimiento. | Convencion local comprobable para tests Python. |
| Las reglas del agente describen el repositorio. | La version inicial de `.agents/rules.md` enumeraba carpetas no existentes y contenia una errata en el lenguaje. | Las reglas iniciales no reflejaban la estructura real; se corrigieron en un commit separado. |

## Discrepancias documentadas

- El README describe una API central FastAPI, pero el repositorio no incluye implementacion ni manifiesto de dependencias para esa API.
- `inventoryManager/` esta en la raiz, aunque el README reserva `services/` para APIs. Es un ejemplo previo, no una convencion suficiente para moverlo sin aprobacion.
- El ejemplo tiene un esquema SQLite con restricciones e inmutabilidad, pero la API opera sobre memoria; no constituye una persistencia de produccion.
- La guia del devcontainer llama a `uv sync` sin que exista un `pyproject.toml` en este checkout.
- El briefing recibido describe HealthCore y sus departamentos, pero no especifica tipos de incidencia, severidades ni canales.

## Reglas derivadas

- Seguir los limites de `services/`, `uis/` y `docs/` descritos en sus README.
- Mantener `snake_case` en Python y SQL, clases `PascalCase` y tests Python con `unittest`, segun `inventoryManager/`.
- No introducir una dependencia o framework sin explicar por que; resolver y documentar la discrepancia entre FastAPI recomendado y WSGI existente antes de fijar el runtime.
- Obtener todos los valores de catalogo del briefing especifico, no de supuestos.
- Registrar cada cambio de estado y area responsable con autor y marca temporal consultables.
- Minimizar datos de salud y no almacenar identificadores directos de pacientes en incidencias operativas.

## Propuesta de mejora no aplicada

Anadir en una tarea de plataforma un manifiesto raiz y un comando de desarrollo/pruebas reproducible para los servicios, y alinear el post-create del devcontainer con ese manifiesto. No se aplica aqui para no ampliar el alcance ni introducir una decision de dependencias antes de acordar el runtime.

## Fuentes

- [README del monorepo](../README.md)
- [README de servicios](../services/README.md)
- [README de interfaces](../uis/README.md)
- [Ejemplo de inventario](../inventoryManager/README.md)
- [API WSGI de inventario](../inventoryManager/api.py)
- [Esquema SQL de inventario](../inventoryManager/schema.sql)
- [Setup del devcontainer](../.devcontainer/post-create.sh)
- [Reglas del agente](../.agents/rules.md)
