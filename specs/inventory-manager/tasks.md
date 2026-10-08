# Tareas de implementacion: inventario de HealthCore

Cada tarea es un bloque pequeno, implementable en orden y verificable contra los IDs EARS de `spec.md`. Cada commit de codigo debe mencionar el `TASK-*` correspondiente; las pruebas de cada comportamiento se incluyen en el commit que lo implementa.

## Orden de implementacion

- [x] **TASK-001 - Persistencia y modelo de articulos** (INV-001, INV-002): definir tablas SQLite para articulos y operaciones de alta/edicion; validar identificador, nombre, unidad y punto de reorden no negativo. El articulo no tendra columna de existencia.
- [ ] **TASK-002 - Identidad y relacion de lotes** (MOV-001, EXC-003): persistir lotes asociados a un articulo, crear el lote al recibir una entrada nueva dentro de la misma transaccion y rechazar un lote reutilizado para otro articulo.
- [ ] **TASK-003 - Registro trazable de movimientos** (MOV-002, MOV-004, EXC-004): persistir entradas, salidas y ajustes con motivo requerido, marca UTC de servidor, cantidad segun tipo e inmutabilidad append-only.
- [ ] **TASK-004 - Existencia derivada e invariante** (MOV-003, INV-004, EXC-001, EXC-002): calcular stock con vista agregada de movimientos y protegerlo en servicio y SQLite; movimientos invalidos o negativos deben revertir por completo.
- [ ] **TASK-005 - Lectura de inventario y punto de reorden** (INV-003, ALR-001, ALR-002): devolver articulos con existencia calculada y exponer alerta cuando stock sea estrictamente menor que el punto de reorden.
- [ ] **TASK-006 - API FastAPI** (INV-001, INV-002, INV-003, MOV-001, MOV-002, ALR-001, ALR-002, EXC-001, EXC-002, EXC-003, EXC-004): exponer contratos HTTP para articulos, lotes, movimientos e inventario bajo el umbral; traducir validaciones a respuestas verificables.
- [ ] **TASK-007 - Backoffice de inventario** (INV-001, INV-002, INV-003, MOV-001, MOV-002, ALR-001, ALR-002): implementar alta/edicion/listado, registro de movimientos con motivo y alerta visible de bajo stock usando la API y sin stock editable.
- [ ] **TASK-008 - Verificacion de aceptacion y documentacion** (INV-001, INV-002, INV-003, INV-004, MOV-001, MOV-002, MOV-003, MOV-004, ALR-001, ALR-002, EXC-001, EXC-002, EXC-003, EXC-004): ejecutar pruebas unitarias, SQLite, API y UI para cada criterio; documentar como ejecutar y actualizar progreso/README.

## Definition of done

- [ ] Cada criterio EARS tiene al menos una prueba automatizada con un nombre que incluya su ID.
- [ ] Los tests cubren tanto resultados correctos como errores, incluyendo stock negativo, articulo inexistente y lote inexistente/ajeno.
- [ ] La salida de tests, `git diff --check` y revision del diff se completan antes de cerrar cada commit.
- [ ] El historial contiene commits pequenos y trazables; no se agrupan todos los cambios en un commit final.
