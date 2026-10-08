# Backoffice de inventario

Interfaz web para consultar articulos de inventario de las clinicas, crear y editar metadatos, registrar movimientos por lote y consultar el historial de cada articulo. La existencia se muestra como dato calculado por la API; no hay un control para editarla.

El panel muestra una alerta visible cuando la existencia es estrictamente inferior al punto de reorden. Los ajustes permiten una cantidad firmada distinta de cero y las salidas requieren un lote existente. Todos los movimientos requieren motivo.

## Ejecutar

Instala las dependencias y sigue las instrucciones de [`inventoryManager/README.md`](../../../inventoryManager/README.md). El servidor FastAPI sirve esta interfaz en `/` junto con la API.

Los nombres y unidades son configurables por HealthCore; no se incluye un catalogo fijo porque el briefing no lo define. No se deben incluir datos de pacientes.