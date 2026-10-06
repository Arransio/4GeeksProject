# Backoffice de incidencias

UI web estática servida por `services.incident_manager.api`. La pantalla incluye el listado centralizado, filtros por estado/severidad/área, resumen de incidencias abiertas por severidad, registro y edición, reasignación, transición de estado e historial cronológico de actor y marca temporal.

Los tipos, severidades, canales, estados y transiciones se cargan desde `/api/catalogs`; la interfaz no define catálogos alternativos. El panel requiere que el servicio se haya iniciado con un archivo de catálogos aprobado. El campo de responsable envía `X-Actor`, pero no sustituye autenticación: integrar SSO/autorización antes de cualquier despliegue.

La descripción advierte no incluir datos identificables de pacientes. La herramienta es un registro operativo y no debe usarse como expediente clínico.