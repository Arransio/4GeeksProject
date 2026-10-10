# Estado del trabajo: gestor de incidencias

## Punto de partida

- Rama: `feature/incident-manager`.
- Base: `origin/dev` en `53f18db`; la rama conserva los commits anteriores hasta `3e51c94`.
- El backend FastAPI/Uvicorn, la persistencia SQLite y el backoffice estatico estan implementados en `services/incident_manager/` y `uis/backoffice/incidents/`.
- Los tipos, severidades, canales, areas y el ciclo de estados fueron aprobados y están configurados en `services/incident_manager/catalogs.json`.
- La API usa FastAPI/Uvicorn conforme a la recomendación del monorepo; dependencias de runtime y test están separadas.
- Commit de reglas: `27dffb3` (`docs: align agent rules with repository conventions`), fechado el 6 de octubre de 2026 a peticion del usuario.
- Commit de contexto y reconocimiento: `7d9b047`, fechado el 6 de octubre de 2026.
- Commit de API/servicio y pruebas: `3b05a9a`, fechado el 6 de octubre de 2026.
- Commit de backoffice: `8febfc6`, fechado el 6 de octubre de 2026.

## Completado en esta iteracion

- Corregidas reglas que no correspondian con la estructura observada del monorepo.
- Corregida en `AGENTS.md` la referencia mal escrita a `memory-bank/techcontext.md`.
- Registrados el contexto conocido de HealthCore, el stack observado y las discrepancias en `memory-bank/` y `docs/`.
- Implementados registro/edicion/listado, filtros, asignacion, ciclo configurable de estados, historial de auditoria y resumen de abiertas por severidad.
- Añadidas pruebas de dominio y API; 10 pruebas pasan con el Python 3.7 disponible y cargan `catalogs.json`.
- Verificada en navegador la UI con catálogos aprobados; el layout a 390 px no produce desbordamiento horizontal.

## Pendiente antes de cerrar

- Añadir al PR el resumen, discrepancias y reglas derivadas, y solicitar aprobacion antes del merge.
- Publicar `feature/incident-manager` y abrir el PR hacia `main`.

La autenticacion SSO no forma parte del alcance de esta tarea. `X-Actor` contiene el actor declarado para cumplir la trazabilidad solicitada; no representa una identidad autenticada.

## Iteracion: infraestructura de agentes (`feature/agent-memory-bank`)

Rama creada desde `feature/inventory-manager`; commits fechados el 10 de octubre de 2026 a peticion del usuario.

- `bd7b5e3` (`docs: map application layer in memory bank and agent rules`): la capa de aplicacion queda mapeada en `memory-bank/techcontext.md` y `.agents/rules.md` — web publica en `uis/website/`, app interna en `uis/backoffice/`, APIs en `services/`, sin arboles paralelos.
- `4d1b0f3` (`docs: declare application scope for agent rules`): cada bloque de `.agents/rules.md` declara su alcance (siempre activa, por patron de archivo o solicitada al agente).
- `35cb114` (`feat(skills): add code review skill with verifiable criteria`): skill de revision pre-commit en `skills/code-review/` con objetivo unico, inputs documentados y 6 criterios de aceptacion verificados por `scripts/check_skill.py` (5 tests OK).
- `bc3874e` (`docs: address the user with neutral masculine wording`): las referencias a quien aprueba quedan redactadas como "el usuario" en `memory-bank/implementation-plan.md` y `memory-bank/progress.md`.
- `AGENTS.md` ya definia el flujo de al menos 4 pasos previos al commit y la lectura inicial del banco de memoria; el banco ya contiene contexto de negocio (`projectbrief.md`) y tecnico (`techcontext.md`).

Proximos pasos: abrir el PR hacia `main`, solicitar revision y, tras el merge, continuar en la siguiente rama desde codigo actualizado.
