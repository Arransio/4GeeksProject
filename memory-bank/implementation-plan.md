# Plan de implementacion: gestor de incidencias

1. Confirmar los catalogos de tipos, severidades y canales contra el BRIEFING.md de la tarea. Usar las areas y responsables ya definidos para HealthCore.
2. Especificar los estados y transiciones permitidos, los campos de la incidencia y las reglas de asignacion antes de escribir la funcionalidad.
3. Implementar persistencia de incidencias y eventos de auditoria. Cada cambio de estado o area debe guardar actor y fecha/hora y poder consultarse desde la incidencia.
4. Exponer operaciones para crear, editar, listar y consultar incidencias, junto con filtros por estado, severidad y area y un resumen de abiertas por severidad.
5. Construir el backoffice en `uis/backoffice/` usando los catalogos confirmados y conectarlo al servicio.
6. Probar registro, clasificacion, asignacion, todas las transiciones, auditoria, filtros, resumen y validaciones de catalogos.
7. Ejecutar las pruebas, revisar el diff, actualizar `memory-bank/progress.md` y documentar en el PR las reglas aplicadas y las discrepancias del repositorio.

La configuracion definitiva y la aceptacion funcional dependen de confirmar los catalogos y transiciones que no aparecen en el briefing recibido.

## Propuesta de catalogos para aprobacion

Esta lista no se carga en la aplicacion ni se trata como requisito confirmado. Se ofrece para que Operaciones y la CTO la contrasten y aprueben:

- Tipos: disponibilidad de clinica/sede, sistemas y accesos, equipamiento, proceso operativo, privacidad/cumplimiento, facturacion y experiencia del paciente.
- Severidades: critica (riesgo inmediato para seguridad/privacidad o interrupcion de multiples sedes), alta (servicio o cumplimiento materialmente afectado), media (impacto parcial con alternativa), baja (incidencia localizada sin interrupcion relevante).
- Canales: llamada de clinica, correo operativo, reporte interno del backoffice, alerta automatizada y escalado de cumplimiento.

Confirmar los nombres finales, criterios y canales con HealthCore antes de configurar la instancia. Los estados y transiciones tambien requieren validacion de Operaciones; los del archivo de pruebas son solo fixtures.
