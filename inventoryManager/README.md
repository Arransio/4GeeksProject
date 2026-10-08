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

La API escucha en `http://127.0.0.1:8001`. Variables opcionales: `INVENTORY_HOST` y `INVENTORY_PORT`.

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