# Especificacion: inventario de HealthCore

## Contexto y alcance

HealthCore opera 12 clinicas y el briefing describe operaciones clinicas, personal e infraestructura, pero no proporciona un catalogo fijo de articulos ni unidades de medida. Este gestor cubre insumos operativos y clinicos consumibles de las clinicas. El nombre del articulo y su unidad son datos configurables por HealthCore; no se fija una taxonomia que el briefing no define. Los datos de pacientes quedan fuera del sistema.

El alcance de esta entrega es el alta, edicion y consulta de articulos; el registro trazable de movimientos; el calculo derivado de existencias; el control por lote; y una alerta visible cuando un articulo baja de su punto de reorden.

## Entidades

- **Articulo:** identificador estable, nombre, unidad de medida y punto de reorden entero no negativo.
- **Lote:** identificador de lote asociado a un unico articulo. El primer movimiento de entrada puede darlo de alta; los demas movimientos deben referirse a un lote existente del mismo articulo.
- **Movimiento:** identificador, articulo, lote, tipo (`entrada`, `salida` o `ajuste`), cantidad entera, motivo obligatorio y marca temporal UTC generada por el sistema. Entrada y salida reciben cantidades positivas; ajuste recibe una cantidad con signo distinto de cero.
- **Existencia:** valor calculado como suma de los deltas de todos los movimientos del articulo y nunca almacenado como campo editable del articulo.

## Requisitos EARS

### Articulos

- **INV-001 (Evento):** Cuando un operador registra un articulo con identificador unico, nombre, unidad y punto de reorden valido, el sistema debe guardarlo sin aceptar un campo de existencia editable.
- **INV-002 (Evento):** Cuando un operador modifica el nombre, unidad o punto de reorden de un articulo existente, el sistema debe guardar esos datos sin modificar ni sustituir sus movimientos.
- **INV-003 (Evento):** Cuando un operador consulta el inventario, el sistema debe listar cada articulo con su identificador, nombre, unidad, punto de reorden y existencia calculada desde sus movimientos.

### Lotes y movimientos

- **MOV-001 (Evento):** Cuando se registra una entrada con un articulo existente y un identificador de lote nuevo, el sistema debe crear el lote y registrar cantidad, motivo y marca temporal UTC en una sola operacion.
- **MOV-002 (Evento):** Cuando se registra una entrada, salida o ajuste para un lote existente que pertenece al articulo indicado, el sistema debe guardar un movimiento inmutable con cantidad valida, motivo no vacio y marca temporal UTC.
- **MOV-003 (Evento):** Cuando el sistema calcula la existencia de un articulo, debe sumar entradas, restar salidas y aplicar los ajustes con su signo, agregando todos sus lotes.
- **MOV-004 (Estado):** Mientras exista un movimiento registrado, el sistema debe impedir que se edite o elimine; una correccion debe registrarse como un movimiento compensatorio.

### Alertas y comportamientos no deseados

- **ALR-001 (Estado):** Mientras la existencia calculada de un articulo sea menor que su punto de reorden, el backoffice debe mostrar una alerta visible para ese articulo.
- **ALR-002 (Estado):** Mientras la existencia calculada sea igual o superior al punto de reorden, el backoffice no debe mostrar la alerta de bajo stock.
- **INV-004 (Invariante):** En todo momento, la existencia calculada de cada articulo debe ser mayor o igual que cero; no debe existir una operacion para editarla directamente.
- **EXC-001 (Comportamiento no deseado):** Si una salida o un ajuste negativo dejara la existencia del articulo por debajo de cero, el sistema debe rechazar el movimiento y conservar sin cambios existencias, lotes y movimientos.
- **EXC-002 (Comportamiento no deseado):** Si un movimiento referencia un articulo inexistente, el sistema debe rechazarlo sin crear lote ni movimiento.
- **EXC-003 (Comportamiento no deseado):** Si una salida o un ajuste referencia un lote inexistente o perteneciente a otro articulo, el sistema debe rechazarlo sin modificar inventario.
- **EXC-004 (Comportamiento no deseado):** Si un movimiento no incluye motivo o su cantidad no es valida para el tipo, el sistema debe rechazarlo sin persistir cambios.

## Criterios de aceptacion y pruebas

| ID | Comprobacion automatizada |
| --- | --- |
| INV-001 | Alta correcta, identificador duplicado rechazado y punto de reorden negativo rechazado. |
| INV-002 | Edicion de campos permitidos preserva el historial de movimientos y rechaza editar existencia. |
| INV-003 | Listado incluye existencia derivada y metadatos de articulo. |
| MOV-001 | Entrada a lote nuevo crea lote y movimiento atomica y trazablemente. |
| MOV-002 | Entrada, salida y ajuste conservan motivo y marca temporal UTC. |
| MOV-003, INV-004 | Stock coincide con la suma de movimientos de todos los lotes y nunca se asigna directamente. |
| MOV-004 | Intentos de modificar/eliminar movimiento se rechazan; el ajuste compensatorio se conserva. |
| ALR-001, ALR-002 | Alerta aparece por debajo del umbral y no aparece exactamente en el umbral. |
| EXC-001 | Salida o ajuste que haria negativo el stock se rechaza atomicamente. |
| EXC-002 | Movimiento de articulo inexistente se rechaza sin cambios. |
| EXC-003 | Salida de lote inexistente o ajeno al articulo se rechaza sin cambios. |
| EXC-004 | Motivo vacio y cantidades no validas se rechazan. |

Las pruebas usan articulos y lotes de ejemplo como datos de test, no como catalogo oficial de HealthCore.
