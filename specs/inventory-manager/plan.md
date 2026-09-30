### PLAN DE IMPLEMENTACION

## Modelo de datos
-Tabla de articulos: identificadores unicos para cada producto. 
-tabla de movimientos: registra de manera inmutable cada operacion con distintos datos asociados (item producto, costo, id propio...)

## Calculo de Stock
-El stock disponible se calcula de manera agregada sumando todas las entradas y devoluciones, y restando las ventas y mermas registradas.
-Se establece una validación estricta para asegurar que el resultado numérico nunca sea inferior a 0.

## Ubicación de la lógica 
-Backend/API: la logica de negocio reside en el servidor.