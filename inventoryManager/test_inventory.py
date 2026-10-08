"""Tests for stock aggregation from immutable movement records."""

from __future__ import annotations

import unittest
import io
import json
import sqlite3
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from inventory import (
    InventoryService,
    InventoryReconciliation,
    Lot,
    InvoiceLine,
    InvoiceValidationError,
    InvalidScan,
    Movement as InventoryMovement,
    MovementType,
    Product,
    Scan,
    StockWouldBecomeNegative,
    SupplierInvoice,
    TerminalLockedError,
)
from api import create_app


def make_movement(*args, **kwargs):
    kwargs.setdefault("lot_id", "LOT-TEST")
    kwargs.setdefault("reason", "Test fixture movement")
    return InventoryMovement(*args, **kwargs)


class InventoryStockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inventory = InventoryService()
        self.inventory.add_product(Product(product_id="P-1", name="Coffee"))
        self.inventory.add_lot(Lot("LOT-TEST", "P-1"))

    def test_stock_is_aggregated_from_all_movements(self) -> None:
        self.inventory.register_movement(
            make_movement("M-1", "P-1", MovementType.RECEIPT, 12, Decimal("2.50"))
        )
        self.inventory.register_movement(
            make_movement("M-2", "P-1", MovementType.RETURN, 2)
        )
        self.inventory.register_movement(
            make_movement("M-3", "P-1", MovementType.SALE, 5)
        )
        self.inventory.register_movement(
            make_movement("M-4", "P-1", MovementType.SHRINKAGE, 1)
        )

        self.assertEqual(self.inventory.get_stock("P-1"), 8)
        database_stock = self.inventory._connection.execute(
            "SELECT stock FROM product_stock WHERE product_id = ?", ("P-1",)
        ).fetchone()[0]
        self.assertEqual(self.inventory.get_stock("P-1"), database_stock)
        movements = self.inventory.get_movements("P-1")
        self.assertTrue(all(movement.reason for movement in movements))
        self.assertTrue(all(movement.occurred_at for movement in movements))

    def test_product_has_no_direct_stock_field(self) -> None:
        product = self.inventory._products["P-1"]
        self.assertFalse(hasattr(product, "stock"))
        with self.assertRaises(AttributeError):
            product.stock = 10  # type: ignore[attr-defined]

    def test_product_can_be_edited_and_listed_without_changing_stock(self) -> None:
        self.inventory.register_movement(
            make_movement("M-PRODUCT-1", "P-1", MovementType.RECEIPT, 7)
        )

        updated = self.inventory.update_product(
            "P-1", name="Examination gloves", unit="box", reorder_point=4
        )

        self.assertEqual(updated.name, "Examination gloves")
        self.assertEqual(updated.unit, "box")
        self.assertEqual(updated.reorder_point, 4)
        self.assertEqual(self.inventory.get_stock("P-1"), 7)
        self.assertEqual(self.inventory.list_products(), (updated,))

    def test_product_catalog_persists_across_service_restarts(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            database_path = str(Path(temporary_directory) / "inventory.sqlite3")
            service = InventoryService(database_path=database_path)
            service.add_product(Product("P-PERSIST", "Exam gloves", "box", 3))
            service.close()

            reopened = InventoryService(database_path=database_path)
            try:
                self.assertEqual(
                    reopened.get_product("P-PERSIST"),
                    Product("P-PERSIST", "Exam gloves", "box", 3),
                )
            finally:
                reopened.close()

    def test_product_rejects_invalid_reorder_point_and_empty_unit(self) -> None:
        with self.assertRaisesRegex(ValueError, "Reorder point"):
            self.inventory.add_product(Product("P-BAD", "Gloves", "box", -1))
        with self.assertRaisesRegex(ValueError, "unit"):
            self.inventory.add_product(Product("P-BAD", "Gloves", "", 0))

    def test_inventory_view_includes_derived_stock_and_reorder_alert_boundary(self) -> None:
        self.inventory.update_product("P-1", reorder_point=3)
        self.inventory.register_movement(
            make_movement("M-REORDER-1", "P-1", MovementType.RECEIPT, 2)
        )

        inventory_rows = self.inventory.list_inventory()
        low_stock_rows = self.inventory.get_low_stock_products()
        self.assertEqual(inventory_rows[0]["stock"], 2)
        self.assertEqual(inventory_rows[0]["reorder_point"], 3)
        self.assertEqual(low_stock_rows, inventory_rows)

        self.inventory.register_movement(
            make_movement("M-REORDER-2", "P-1", MovementType.RECEIPT, 1)
        )
        self.assertEqual(self.inventory.get_stock("P-1"), 3)
        self.assertEqual(self.inventory.get_low_stock_products(), ())

    def test_lot_belongs_to_one_existing_product(self) -> None:
        self.inventory.add_product(Product("P-2", "Exam masks", "box", 2))
        self.inventory.add_lot(Lot("LOT-1", "P-1"))

        self.assertEqual(self.inventory.get_lot("LOT-1"), Lot("LOT-1", "P-1"))
        self.assertEqual(
            self.inventory.list_lots("P-1"),
            (Lot("LOT-1", "P-1"), Lot("LOT-TEST", "P-1")),
        )
        self.assertEqual(self.inventory.list_lots("P-2"), ())
        with self.assertRaises(sqlite3.IntegrityError):
            self.inventory.add_lot(Lot("LOT-1", "P-2"))

    def test_lot_rejects_unknown_product_and_persists(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown product"):
            self.inventory.add_lot(Lot("LOT-UNKNOWN", "P-404"))

        with TemporaryDirectory() as temporary_directory:
            database_path = str(Path(temporary_directory) / "inventory.sqlite3")
            service = InventoryService(database_path=database_path)
            service.add_product(Product("P-LOT", "Test kits", "kit", 1))
            service.add_lot(Lot("LOT-PERSIST", "P-LOT"))
            service.close()

            reopened = InventoryService(database_path=database_path)
            try:
                self.assertEqual(
                    reopened.get_lot("LOT-PERSIST"), Lot("LOT-PERSIST", "P-LOT")
                )
            finally:
                reopened.close()

    def test_duplicate_movement_is_rejected(self) -> None:
        movement = make_movement("M-1", "P-1", MovementType.RECEIPT, 3)
        self.inventory.register_movement(movement)

        with self.assertRaisesRegex(ValueError, "Movement already exists"):
            self.inventory.register_movement(movement)

    def test_movement_requires_reason_and_is_persisted_as_immutable(self) -> None:
        with self.assertRaisesRegex(ValueError, "reason"):
            self.inventory.register_movement(
                InventoryMovement("M-NO-REASON", "P-1", MovementType.RECEIPT, 2)
            )

        movement = make_movement("M-IMMUTABLE", "P-1", MovementType.RECEIPT, 2)
        self.inventory.register_movement(movement)
        stored = self.inventory._connection.execute(
            "SELECT reason, occurred_at FROM movements WHERE movement_id = ?",
            ("M-IMMUTABLE",),
        ).fetchone()
        self.assertEqual(stored["reason"], "Test fixture movement")
        self.assertTrue(stored["occurred_at"].endswith("+00:00"))
        with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
            self.inventory._connection.execute(
                "UPDATE movements SET reason = 'changed' WHERE movement_id = ?",
                ("M-IMMUTABLE",),
            )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
            self.inventory._connection.execute(
                "DELETE FROM movements WHERE movement_id = ?", ("M-IMMUTABLE",)
            )

    def test_movements_persist_across_service_restarts(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            database_path = str(Path(temporary_directory) / "movement.sqlite3")
            service = InventoryService(database_path=database_path)
            service.add_product(Product("P-RESTART", "Gloves", "box", 2))
            service.add_lot(Lot("LOT-RESTART", "P-RESTART"))
            service.register_movement(
                make_movement(
                    "M-RESTART",
                    "P-RESTART",
                    MovementType.RECEIPT,
                    5,
                    lot_id="LOT-RESTART",
                    reason="Clinic delivery",
                )
            )
            service.close()

            reopened = InventoryService(database_path=database_path)
            try:
                self.assertEqual(reopened.get_stock("P-RESTART"), 5)
                self.assertEqual(len(reopened.get_movements("P-RESTART")), 1)
                movement = reopened.get_movements("P-RESTART")[0]
                self.assertEqual(movement.reason, "Clinic delivery")
                self.assertEqual(movement.lot_id, "LOT-RESTART")
                self.assertTrue(movement.occurred_at)
            finally:
                reopened.close()

    def test_legacy_database_migrates_existing_movements(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            database_path = str(Path(temporary_directory) / "legacy.sqlite3")
            connection = sqlite3.connect(database_path)
            connection.executescript(
                """
                CREATE TABLE products (product_id TEXT PRIMARY KEY, name TEXT NOT NULL);
                CREATE TABLE movements (
                    movement_id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL,
                    movement_type TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_cost NUMERIC,
                    reference_id TEXT
                );
                INSERT INTO products VALUES ('P-LEGACY', 'Gloves');
                INSERT INTO movements VALUES ('M-LEGACY', 'P-LEGACY', 'receipt', 6, NULL, 'old invoice');
                """
            )
            connection.close()

            migrated = InventoryService(database_path=database_path)
            try:
                movements = migrated.get_movements("P-LEGACY")
                self.assertEqual(migrated.get_stock("P-LEGACY"), 6)
                self.assertEqual(movements[0].reason, "Legacy movement")
                self.assertTrue(movements[0].lot_id.startswith("LEGACY-"))
                self.assertTrue(movements[0].occurred_at)
            finally:
                migrated.close()

    def test_new_lot_and_movement_are_rolled_back_together(self) -> None:
        movement = make_movement(
            "M-ATOMIC-1",
            "P-1",
            MovementType.RECEIPT,
            2,
            lot_id="LOT-ATOMIC",
            reason="Clinic delivery",
        )
        self.inventory._movement_ids.add("M-ATOMIC-1")

        with self.assertRaisesRegex(ValueError, "Movement already exists"):
            self.inventory._commit_movements((movement,))

        with self.assertRaisesRegex(ValueError, "Unknown lot"):
            self.inventory.get_lot("LOT-ATOMIC")

    def test_stock_cannot_fall_below_zero(self) -> None:
        with self.assertRaises(StockWouldBecomeNegative) as context:
            self.inventory.register_movement(
                make_movement("M-1", "P-1", MovementType.SALE, 1)
            )

        self.assertEqual(context.exception.current_stock, 0)
        self.assertEqual(context.exception.delta, -1)
        self.assertEqual(self.inventory.get_stock("P-1"), 0)
        self.assertEqual(self.inventory.get_movements("P-1"), ())

    def test_movement_cannot_take_positive_stock_below_zero(self) -> None:
        self.inventory.register_movement(
            make_movement("M-1", "P-1", MovementType.RECEIPT, 4)
        )

        with self.assertRaises(StockWouldBecomeNegative):
            self.inventory.register_movement(
                make_movement("M-2", "P-1", MovementType.SALE, 5)
            )

        self.assertEqual(self.inventory.get_stock("P-1"), 4)

    def test_scan_of_exactly_one_item_is_accepted_once(self) -> None:
        self.inventory.validate_scan(Scan("S-1", "P-1", 1))

        with self.assertRaisesRegex(InvalidScan, "already processed"):
            self.inventory.validate_scan(Scan("S-1", "P-1", 1))

    def test_scan_cannot_represent_multiple_items(self) -> None:
        with self.assertRaisesRegex(InvalidScan, "exactly one item"):
            self.inventory.validate_scan(Scan("S-2", "P-1", 2))

        # A rejected scan does not consume the scan id.
        self.inventory.validate_scan(Scan("S-2", "P-1", 1))

    def test_scan_rejects_boolean_count_and_unknown_product(self) -> None:
        with self.assertRaises(InvalidScan):
            self.inventory.validate_scan(Scan("S-3", "P-1", True))
        with self.assertRaisesRegex(InvalidScan, "unknown product"):
            self.inventory.validate_scan(Scan("S-4", "P-404", 1))

    def test_invoice_receipt_adds_verified_quantities_to_stock(self) -> None:
        invoice = SupplierInvoice(
            "INV-100",
            (InvoiceLine("P-1", 2, Decimal("2.50")),),
        )
        scans = (Scan("S-10", "P-1"), Scan("S-11", "P-1"))

        movements = self.inventory.receive_invoice(invoice, scans)

        self.assertEqual(len(movements), 1)
        self.assertEqual(movements[0].movement_type, MovementType.RECEIPT)
        self.assertEqual(movements[0].quantity, 2)
        self.assertEqual(movements[0].unit_cost, Decimal("2.50"))
        self.assertEqual(movements[0].reference_id, "INV-100")
        self.assertEqual(self.inventory.get_stock("P-1"), 2)

    def test_invoice_rejects_mismatched_scanned_quantity_atomically(self) -> None:
        invoice = SupplierInvoice("INV-101", (InvoiceLine("P-1", 2),))

        with self.assertRaisesRegex(InvoiceValidationError, "do not match"):
            self.inventory.receive_invoice(invoice, (Scan("S-12", "P-1"),))

        self.assertEqual(self.inventory.get_stock("P-1"), 0)
        self.assertEqual(self.inventory.get_movements("P-1"), ())
        # The failed transaction did not consume IDs; a corrected retry works.
        self.inventory.receive_invoice(
            invoice, (Scan("S-12", "P-1"), Scan("S-13", "P-1"))
        )
        self.assertEqual(self.inventory.get_stock("P-1"), 2)

    def test_invoice_rejects_multiple_items_per_scan(self) -> None:
        invoice = SupplierInvoice("INV-102", (InvoiceLine("P-1", 2),))

        with self.assertRaisesRegex(InvoiceValidationError, "exactly one"):
            self.inventory.receive_invoice(invoice, (Scan("S-14", "P-1", 2),))

        self.assertEqual(self.inventory.get_movements("P-1"), ())

    def test_invoice_cannot_be_processed_twice(self) -> None:
        invoice = SupplierInvoice("INV-103", (InvoiceLine("P-1", 1),))
        scan = Scan("S-15", "P-1")
        self.inventory.receive_invoice(invoice, (scan,))

        with self.assertRaisesRegex(InvoiceValidationError, "already processed"):
            self.inventory.receive_invoice(
                invoice, (Scan("S-16", "P-1"),)
            )

        self.assertEqual(self.inventory.get_stock("P-1"), 1)

    def test_scanned_return_adds_items_to_stock(self) -> None:
        movements = self.inventory.record_return(
            "RET-1", (Scan("S-20", "P-1"), Scan("S-21", "P-1")), "checkout-1"
        )

        self.assertEqual(len(movements), 1)
        self.assertEqual(movements[0].movement_type, MovementType.RETURN)
        self.assertEqual(movements[0].quantity, 2)
        self.assertEqual(self.inventory.get_stock("P-1"), 2)

    def test_checkout_sale_reduces_stock(self) -> None:
        self.inventory.register_movement(
            make_movement("M-20", "P-1", MovementType.RECEIPT, 3)
        )

        movements = self.inventory.record_sale(
            "SALE-1", (Scan("S-22", "P-1"), Scan("S-23", "P-1")), "checkout-2"
        )

        self.assertEqual(movements[0].movement_type, MovementType.SALE)
        self.assertEqual(movements[0].quantity, 2)
        self.assertEqual(self.inventory.get_stock("P-1"), 1)

    def test_checkout_sale_that_exceeds_stock_locks_terminal(self) -> None:
        self.inventory.register_movement(
            make_movement("M-21", "P-1", MovementType.RECEIPT, 1)
        )

        with self.assertRaises(StockWouldBecomeNegative):
            self.inventory.record_sale(
                "SALE-2", (Scan("S-24", "P-1"), Scan("S-25", "P-1")), "checkout-3"
            )

        self.assertTrue(self.inventory.is_terminal_locked("checkout-3"))
        self.assertEqual(self.inventory.get_stock("P-1"), 1)
        with self.assertRaises(TerminalLockedError):
            self.inventory.record_return(
                "RET-2", (Scan("S-26", "P-1"),), "checkout-3"
            )

    def test_month_end_reconciliation_registers_shrinkage(self) -> None:
        self.inventory.register_movement(
            make_movement("M-22", "P-1", MovementType.RECEIPT, 8)
        )

        movements = self.inventory.reconcile_month_end(
            InventoryReconciliation("STOCKTAKE-1", {"P-1": 5})
        )

        self.assertEqual(len(movements), 1)
        self.assertEqual(movements[0].movement_type, MovementType.SHRINKAGE)
        self.assertEqual(movements[0].quantity, 3)
        self.assertEqual(self.inventory.get_stock("P-1"), 5)

    def test_month_end_reconciliation_records_physical_surplus(self) -> None:
        movements = self.inventory.reconcile_month_end(
            InventoryReconciliation("STOCKTAKE-2", {"P-1": 3})
        )

        self.assertEqual(movements[0].movement_type, MovementType.INVENTORY_GAIN)
        self.assertEqual(self.inventory.get_stock("P-1"), 3)

    def test_manual_negative_movement_locks_and_manager_can_unlock(self) -> None:
        self.inventory = InventoryService(
            manager_credential_verifier=lambda username, password: (
                username == "manager" and password == "valid"
            )
        )
        self.inventory.add_product(Product("P-1", "Coffee"))
        self.inventory.add_lot(Lot("LOT-TEST", "P-1"))

        with self.assertRaises(StockWouldBecomeNegative):
            self.inventory.register_movement(
                make_movement("M-23", "P-1", MovementType.SALE, 1), "manual-terminal"
            )

        self.assertTrue(self.inventory.is_terminal_locked("manual-terminal"))
        self.assertFalse(
            self.inventory.authorize_manager("manual-terminal", "manager", "wrong")
        )
        with self.assertRaises(TerminalLockedError):
            self.inventory.register_movement(
                make_movement("M-24", "P-1", MovementType.RECEIPT, 1), "manual-terminal"
            )

        self.assertTrue(
            self.inventory.authorize_manager("manual-terminal", "manager", "valid")
        )
        self.assertFalse(self.inventory.is_terminal_locked("manual-terminal"))
        self.inventory.register_movement(
            make_movement("M-25", "P-1", MovementType.RECEIPT, 2), "manual-terminal"
        )
        self.assertEqual(self.inventory.get_stock("P-1"), 2)

    def test_wsgi_invoice_endpoint_receives_verified_items(self) -> None:
        app = create_app(self.inventory)
        payload = {
            "invoice": {
                "invoice_id": "INV-API-1",
                "lines": [{"product_id": "P-1", "quantity": 2}],
            },
            "scans": [
                {"scan_id": "S-API-1", "product_id": "P-1"},
                {"scan_id": "S-API-2", "product_id": "P-1"},
            ],
        }
        response: dict[str, object] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            response["status"] = status
            response["headers"] = headers

        result = app(
            {
                "REQUEST_METHOD": "POST",
                "PATH_INFO": "/invoices/receive",
                "CONTENT_LENGTH": str(len(json.dumps(payload).encode("utf-8"))),
                "wsgi.input": io.BytesIO(json.dumps(payload).encode("utf-8")),
            },
            start_response,
        )

        self.assertEqual(response["status"], "201 Created")
        body = json.loads(b"".join(result))
        self.assertEqual(body["invoice_id"], "INV-API-1")
        self.assertEqual(self.inventory.get_stock("P-1"), 2)

    def test_sqlite_schema_guards_negative_aggregate_stock(self) -> None:
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        connection = sqlite3.connect(":memory:")
        connection.executescript(schema)
        connection.execute(
            "INSERT INTO products (product_id, name) VALUES (?, ?)", ("P-DB", "Tea")
        )
        connection.execute(
            "INSERT INTO lots (lot_id, product_id) VALUES (?, ?)", ("LOT-DB", "P-DB")
        )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "stock cannot be negative"):
            connection.execute(
                """INSERT INTO movements
                         (movement_id, product_id, lot_id, movement_type, quantity, reason, occurred_at)
                         VALUES (?, ?, ?, ?, ?, ?, ?)""",
                     ("M-DB-1", "P-DB", "LOT-DB", "sale", 1, "Test sale", "2026-10-06T00:00:00+00:00"),
            )

        connection.execute(
            """INSERT INTO movements
                    (movement_id, product_id, lot_id, movement_type, quantity, reason, occurred_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("M-DB-2", "P-DB", "LOT-DB", "receipt", 3, "Test receipt", "2026-10-06T00:00:00+00:00"),
        )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "stock cannot be negative"):
            connection.execute(
                """INSERT INTO movements
                         (movement_id, product_id, lot_id, movement_type, quantity, reason, occurred_at)
                         VALUES (?, ?, ?, ?, ?, ?, ?)""",
                     ("M-DB-3", "P-DB", "LOT-DB", "sale", 4, "Test sale", "2026-10-06T00:00:00+00:00"),
            )
        stock = connection.execute(
            "SELECT stock FROM product_stock WHERE product_id = ?", ("P-DB",)
        ).fetchone()[0]
        self.assertEqual(stock, 3)
        connection.close()

    def test_sqlite_schema_rejects_lot_owned_by_another_product(self) -> None:
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        connection = sqlite3.connect(":memory:")
        connection.executescript(schema)
        connection.execute(
            "INSERT INTO products (product_id, name) VALUES (?, ?)", ("P-A", "Gloves")
        )
        connection.execute(
            "INSERT INTO products (product_id, name) VALUES (?, ?)", ("P-B", "Masks")
        )
        connection.execute(
            "INSERT INTO lots (lot_id, product_id) VALUES (?, ?)", ("LOT-A", "P-A")
        )

        with self.assertRaises(sqlite3.IntegrityError):
            connection.execute(
                """INSERT INTO movements
                   (movement_id, product_id, lot_id, movement_type, quantity)
                   VALUES (?, ?, ?, ?, ?)""",
                ("M-WRONG-LOT", "P-B", "LOT-A", "receipt", 2),
            )
        connection.close()


if __name__ == "__main__":
    unittest.main()
