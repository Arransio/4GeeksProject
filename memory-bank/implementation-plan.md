# Plan de implementacion: gestor de incidencias

1. Confirmar los catalogos de tipos, severidades y canales contra el BRIEFING.md de la tarea. Usar las areas y responsables ya definidos para HealthCore.
2. Especificar los estados y transiciones permitidos, los campos de la incidencia y las reglas de asignacion antes de escribir la funcionalidad.
3. Implementar persistencia de incidencias y eventos de auditoria. Cada cambio de estado o area debe guardar actor y fecha/hora y poder consultarse desde la incidencia.
4. Exponer operaciones para crear, editar, listar y consultar incidencias, junto con filtros por estado, severidad y area y un resumen de abiertas por severidad.
5. Construir el backoffice en `uis/backoffice/` usando los catalogos confirmados y conectarlo al servicio.
6. Probar registro, clasificacion, asignacion, todas las transiciones, auditoria, filtros, resumen y validaciones de catalogos.
7. Ejecutar las pruebas, revisar el diff, actualizar `memory-bank/progress.md` y documentar en el PR las reglas aplicadas y las discrepancias del repositorio.

El trabajo de los pasos 3 a 6 depende de confirmar los catalogos que no aparecen en el briefing recibido.
