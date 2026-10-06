# Backoffice de incidencias

UI web estática servida por `services.incident_manager.api`. La pantalla incluye el listado centralizado, filtros por estado/severidad/área, resumen de incidencias abiertas por severidad, registro y edición, reasignación, transición de estado e historial cronológico de actor y marca temporal.

Los tipos, severidades, canales, estados y transiciones se cargan desde `/api/catalogs`; la interfaz no define catálogos alternativos. El panel usa `X-Actor` para enviar el actor declarado que debe quedar en la auditoría.

La descripción advierte no incluir datos identificables de pacientes. La herramienta es un registro operativo y no debe usarse como expediente clínico.