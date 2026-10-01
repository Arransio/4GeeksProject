-- SQLite persistence sketch. Stock is a view over immutable movement rows.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS movements (
    movement_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(product_id),
    movement_type TEXT NOT NULL CHECK (
        movement_type IN ('receipt', 'return', 'sale', 'shrinkage', 'inventory_gain')
    ),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_cost NUMERIC,
    reference_id TEXT
);

CREATE VIEW IF NOT EXISTS product_stock AS
SELECT
    p.product_id,
    COALESCE(SUM(
        CASE
            WHEN m.movement_type IN ('receipt', 'return', 'inventory_gain')
                THEN m.quantity
            WHEN m.movement_type IN ('sale', 'shrinkage')
                THEN -m.quantity
            ELSE 0
        END
    ), 0) AS stock
FROM products AS p
LEFT JOIN movements AS m ON m.product_id = p.product_id
GROUP BY p.product_id;

-- Aggregated invariant: reject any movement that would make stock < 0.
CREATE TRIGGER IF NOT EXISTS movements_stock_nonnegative
BEFORE INSERT ON movements
FOR EACH ROW
WHEN COALESCE((
    SELECT stock FROM product_stock WHERE product_id = NEW.product_id
), 0) + CASE
    WHEN NEW.movement_type IN ('receipt', 'return', 'inventory_gain')
        THEN NEW.quantity
    ELSE -NEW.quantity
END < 0
BEGIN
    SELECT RAISE(ABORT, 'stock cannot be negative');
END;

-- Movement log is append-only: corrections are represented by compensating rows.
CREATE TRIGGER IF NOT EXISTS movements_no_update
BEFORE UPDATE ON movements
BEGIN
    SELECT RAISE(ABORT, 'movements are immutable');
END;

CREATE TRIGGER IF NOT EXISTS movements_no_delete
BEFORE DELETE ON movements
BEGIN
    SELECT RAISE(ABORT, 'movements are immutable');
END;
