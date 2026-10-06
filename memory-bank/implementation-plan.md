# Plan de implementacion: gestor de incidencias

1. Confirmar los catalogos de tipos, severidades y canales contra el BRIEFING.md de la tarea. Usar las areas y responsables ya definidos para HealthCore.
2. Especificar los estados y transiciones permitidos, los campos de la incidencia y las reglas de asignacion antes de escribir la funcionalidad.
3. Implementar persistencia de incidencias y eventos de auditoria. Cada cambio de estado o area debe guardar actor y fecha/hora y poder consultarse desde la incidencia.
4. Exponer operaciones para crear, editar, listar y consultar incidencias, junto con filtros por estado, severidad y area y un resumen de abiertas por severidad.
5. Construir el backoffice en `uis/backoffice/` usando los catalogos confirmados y conectarlo al servicio.
6. Probar registro, clasificacion, asignacion, todas las transiciones, auditoria, filtros, resumen y validaciones de catalogos.
7. Ejecutar las pruebas, revisar el diff, actualizar `memory-bank/progress.md` y documentar en el PR las reglas aplicadas y las discrepancias del repositorio.

Los catálogos de tipos, severidades y canales y el flujo de estados fueron aprobados por la usuaria y están activos en `services/incident_manager/catalogs.json`.

## Catalogos y aprobaciones

### Tipos de incidencia: aprobados por la usuaria

- Disponibilidad de clinica/sede.
- Sistemas y accesos.
- Equipamiento.
- Proceso operativo.
- Privacidad/cumplimiento.
- Facturacion.
- Experiencia del paciente.

La aprobacion confirma estos tipos para la tarea; ya estan incorporados en el archivo de configuracion junto con los demas catalogos aprobados.

### Severidades: aprobadas por la usuaria

- Critica: riesgo inmediato para la seguridad o privacidad, o interrupcion en multiples sedes.
- Alta: afectacion importante del servicio o del cumplimiento.
- Media: afectacion parcial con una alternativa disponible.
- Baja: incidencia localizada sin interrupcion relevante.

### Canales de entrada: aprobados por la usuaria

- Llamada de clinica.
- Correo operativo.
- Reporte interno del backoffice.
- Alerta automatizada.
- Escalado de cumplimiento.

### Estados y transiciones: aprobados por la usuaria

- Abierta → En revisión.
- En revisión → En curso.
- En curso → Resuelta.
- Resuelta → Cerrada.
- Los estados Abierta, En revisión, En curso y Resuelta cuentan como abiertos; Cerrada es el único estado cerrado.

### Pendientes de revision

- No quedan pendientes de aprobación de catálogos.
