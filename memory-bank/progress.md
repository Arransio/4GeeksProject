# Estado del trabajo: gestor de incidencias

## Punto de partida

- Rama: `feature/incident-manager`.
- Base: `origin/dev` en `53f18db`; la rama conserva los commits anteriores hasta `3e51c94`.
- El backend, la API WSGI y el backoffice estatico estan implementados en `services/incident_manager/` y `uis/backoffice/incidents/`.
- Commit de reglas: `27dffb3` (`docs: align agent rules with repository conventions`), fechado el 6 de octubre de 2026 a peticion del usuario.
- Commit de contexto y reconocimiento: `7d9b047`, fechado el 6 de octubre de 2026.
- Commit de API/servicio y pruebas: `3b05a9a`, fechado el 6 de octubre de 2026.
- Commit de backoffice: `8febfc6`, fechado el 6 de octubre de 2026.

## Completado en esta iteracion

- Corregidas reglas que no correspondian con la estructura observada del monorepo.
- Corregida en `AGENTS.md` la referencia mal escrita a `memory-bank/techcontext.md`.
- Registrados el contexto conocido de HealthCore, el stack observado y las discrepancias en `memory-bank/` y `docs/`.
- Implementados registro/edicion/listado, filtros, asignacion, ciclo configurable de estados, historial de auditoria y resumen de abiertas por severidad.
- Añadidas pruebas de dominio y API; 10 pruebas pasan con el Python 3.7 disponible.
- Verificada en navegador una creacion y consulta con catalogos de fixture; el layout a 390 px no produce desbordamiento horizontal.

## Pendiente antes de cerrar

- Aprobar o corregir la propuesta de tipos, severidades y canales con Operaciones/CTO; el briefing recibido no los incluye.
- Validar los estados/transiciones y los criterios que definen una incidencia abierta.
- Crear un archivo de catálogos aprobado y hacer una prueba de aceptación con esos valores; la instancia actual no puede arrancar sin dicha configuración.
- Integrar autenticacion y autorizacion corporativas; `X-Actor` por si solo no verifica la identidad.
- Hacer revision de seguridad y privacidad antes de despliegue, incluida proteccion de acceso, retencion y auditoria.
- Probar el backoffice en navegador con catalogos aprobados y verificar responsive/accesibilidad visualmente.
- Confirmar la decision de runtime con el equipo: se sigue el WSGI estandar del ejemplo aunque el README recomienda FastAPI.
- Añadir al PR el resumen, discrepancias y reglas derivadas, y solicitar aprobacion antes del merge.
- Publicar `feature/incident-manager` y abrir el PR hacia `main` tras completar las aprobaciones anteriores.
