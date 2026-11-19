# Inventario de HealthCore

API FastAPI para gestionar articulos e insumos configurables de las clinicas de HealthCore. La existencia no se almacena en el articulo: SQLite la calcula desde el libro inmutable de movimientos.

## Comportamiento

- Articulos persistidos con identificador, nombre, unidad y punto de reorden; no tienen campo editable de stock.
- Lotes persistidos y asociados a un solo articulo.
- Movimientos `receipt`, `return`, `sale`, `shrinkage`, `inventory_gain` o `adjustment` con lote, razon obligatoria y marca temporal UTC. Un ajuste usa una cantidad firmada no nula.
- Stock derivado mediante la vista SQLite `product_stock`; las restricciones impiden negativos y lotes ajenos.
- Historial append-only: SQLite rechaza UPDATE y DELETE de movimientos.
- Inventario bajo reorden disponible cuando `stock < reorder_point`; en igualdad no genera alerta.
- La recepcion de factura verifica la cantidad escaneada y guarda entradas.

Los nombres y unidades son configurables; el briefing HealthCore no fija un catalogo de articulos. No guardar datos identificables de pacientes en este inventario.

## Instalar y ejecutar

Desde la raiz del repositorio con Python 3.7 o posterior:

```bash
python3 -m pip install -r inventoryManager/requirements.txt
PYTHONPATH=inventoryManager INVENTORY_DATABASE=inventory.sqlite3 python3 -m inventoryManager
```

La API y el backoffice escuchan en `http://127.0.0.1:8766`. El enlace de Incidencias abre `http://127.0.0.1:8765`; ambos puntos se encuentran en la navegacion lateral de las dos pantallas. Variables opcionales: `INVENTORY_HOST` y `INVENTORY_PORT`.

## API

- `POST /api/products`, `GET /api/products`, `GET /api/products/{product_id}`, `PATCH /api/products/{product_id}`
- `GET /api/inventory` y `GET /api/inventory/low-stock`
- `GET /api/products/{product_id}/lots` y `GET /api/products/{product_id}/movements`
- `POST /api/movements`
- `POST /api/invoices/receive`
- `POST /api/inventory/reconcile`

La misma API sirve el backoffice documentado en [`uis/backoffice/inventory/README.md`](../uis/backoffice/inventory/README.md).

## Pruebas

```bash
python3 -m pip install -r inventoryManager/requirements-dev.txt
PYTHONPATH=inventoryManager python3 -m unittest discover -s inventoryManager -v
```

## Trazabilidad de aceptacion

| Criterio | Test automatizado |
| --- | --- |
| INV-001 | `test_inv_001_product_catalog_persists_across_service_restarts`, `test_inv_001_inv_002_inv_003_alr_001_alr_002_fastapi_product_crud_inventory` |
| INV-002 | `test_inv_002_product_can_be_edited_without_changing_stock`, API CRUD |
| INV-003 | `test_inv_003_alr_001_alr_002_inventory_and_reorder_boundary`, API inventory list |
| INV-004 | `test_inv_001_inv_004_product_has_no_direct_stock_field`, `test_mov_003_inv_004_stock_is_aggregated_from_all_movements` |
| MOV-001 | `test_mov_001_new_lot_and_movement_are_rolled_back_together`, factura FastAPI |
| MOV-002 | `test_mov_002_mov_004_movement_reason_timestamp_and_immutability`, tests de venta y devolucion |
| MOV-003 | `test_mov_003_inv_004_stock_is_aggregated_from_all_movements`, tests de reconciliacion mensual |
| MOV-004 | `test_mov_002_mov_004_movement_reason_timestamp_and_immutability`, `test_mov_004_duplicate_movement_is_rejected` |
| ALR-001, ALR-002 | `test_inv_003_alr_001_alr_002_inventory_and_reorder_boundary`, API CRUD/inventory |
| EXC-001 | Tests `test_exc_001_*` de servicio, terminales y trigger SQLite |
| EXC-002 | `test_exc_002_movement_for_unknown_product_is_rejected` |
| EXC-003 | `test_exc_003_movement_rejects_missing_or_foreign_lot`, FK SQLite |
| EXC-004 | Tests `test_exc_004_*` de motivo, cantidades y verificacion de factura |