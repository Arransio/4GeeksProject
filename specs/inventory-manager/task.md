TASK-001 (Ref. INV-001, INV-002): Implementar la lógica en el backend para calcular el stock exclusivamente de forma agregada a partir de los movimientos registrados, asegurando que no exista un campo de stock modificable de manera directa. 

TASK-002 (Ref. INV-003): Configurar las validaciones a nivel de base de datos y modelo de dominio para garantizar que el stock nunca pueda ser negativo, estableciendo 0 como su límite mínimo. 

TASK-003 (Ref. INV-004): Añadir la regla de validación en el procesamiento de escaneos para asegurar que una lectura individual equivalga estrictamente a un único ítem.   

TASK-004 (Ref. EVT-001): Desarrollar el endpoint y el flujo para recibir mercancía mediante el escaneo de una factura que especifique y verifique el número de cada ítem.   

TASK-005 (Ref. EVT-002): Implementar el registro de devoluciones a través de los escáneres de cajas para sumar correctamente los ítems devueltos.  

TASK-006 (Ref. EVT-003): Implementar la lógica para que las cajas registren las ventas de productos y deduzcan automáticamente su cantidad del stock.  

TASK-007 (Ref. EVT-004): Desarrollar la rutina de inventario de fin de mes para contrastar el stock con la realidad, considerando los ítems desaparecidos como merma y restándolos del stock.   

TASK-008 (Ref. EXC-001, EXC-002): Programar el mecanismo de intercepción de excepciones para que, si un movimiento (automático o manual) deja el stock en negativo, se bloquee el terminal y se soliciten credenciales de encargado.   