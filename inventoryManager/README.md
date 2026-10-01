# Inventory manager — TASK-001 through TASK-008

Backend sketch for INV-001 through INV-004. Stock is computed on demand from
immutable movement records, rather than stored as an editable product field.

## Domain rules

- `receipt` and `return` movements add stock.
- `sale` and `shrinkage` movements subtract stock.
- Movement quantities must be positive, and movement identifiers are unique.
- A movement is rejected with `StockWouldBecomeNegative` if its resulting
  aggregate stock would be below zero; rejected movements are not recorded.
- `validate_scan()` accepts a scan only when its item count is exactly integer
  `1`, it references a known product, and its scan ID has not been processed.
  Invalid or duplicate scans are rejected without being recorded.
- `receive_invoice()` receives decoded invoice data and individual product
  scans, checks that each product's scanned item count exactly matches the
  invoice line, then records receipt movements linked to the invoice. The
  operation is atomic in this in-memory implementation and duplicate invoices
  are rejected.
- `record_return()` groups scanned checkout returns into positive stock
  movements. `record_sale()` groups checkout scans into sales and checks stock
  before committing the complete operation.
- `reconcile_month_end()` compares physical counts for every known product to
  calculated stock. Missing units become `shrinkage`; physical surpluses are
  recorded as `inventory_gain` so ledger stock matches the count.
- Any negative-stock attempt through a terminal locks that terminal and raises
  `StockWouldBecomeNegative`. Other operations at that terminal are blocked
  until `authorize_manager()` accepts credentials through the injected
  verifier. No credential is persisted by this sketch.
- `Product` has no stock property; `InventoryService.get_stock()` is the sole
  stock calculation interface.

The domain service is in-memory, but this sketch now includes a dependency-free
WSGI endpoint (`POST /invoices/receive`) in `api.py` and an executable SQLite
schema in `schema.sql`. The SQLite view derives stock from movements, while
triggers block negative aggregate stock and prevent movement updates/deletes.
The service and SQL database are not yet connected as a single persistent
deployment; the endpoint currently calls the in-memory service. Scanner
hardware and production identity-provider integration remain out of scope.

To serve the WSGI app, create an `InventoryService`, register products, pass it
to `create_app()` and run it with a WSGI server. The manager credential verifier
must be connected to a trusted identity provider before production use.

## Run tests

From this directory, run:

```bash
python -m unittest discover -s . -v
```
