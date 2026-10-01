"""Tests for stock aggregation from immutable movement records."""

import unittest
import io
import json
import sqlite3
from decimal import Decimal
from pathlib import Path

from inventory import (
    InventoryService,
    InventoryReconciliation,
    InvoiceLine,
    InvoiceValidationError,
    InvalidScan,
    Movement,
    MovementType,
    Product,
    Scan,
    StockWouldBecomeNegative,
    SupplierInvoice,
    TerminalLockedError,
)
from api import create_app


class InventoryStockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inventory = InventoryService()
        self.inventory.add_product(Product(product_id="P-1", name="Coffee"))

    def test_stock_is_aggregated_from_all_movements(self) -> None:
        self.inventory.register_movement(
            Movement("M-1", "P-1", MovementType.RECEIPT, 12, Decimal("2.50"))
        )
        self.inventory.register_movement(
            Movement("M-2", "P-1", MovementType.RETURN, 2)
        )
        self.inventory.register_movement(
            Movement("M-3", "P-1", MovementType.SALE, 5)
        )
        self.inventory.register_movement(
            Movement("M-4", "P-1", MovementType.SHRINKAGE, 1)
        )

        self.assertEqual(self.inventory.get_stock("P-1"), 8)

    def test_product_has_no_direct_stock_field(self) -> None:
        product = self.inventory._products["P-1"]
        self.assertFalse(hasattr(product, "stock"))
        with self.assertRaises(AttributeError):
            product.stock = 10  # type: ignore[attr-defined]

    def test_duplicate_movement_is_rejected(self) -> None:
        movement = Movement("M-1", "P-1", MovementType.RECEIPT, 3)
        self.inventory.register_movement(movement)

        with self.assertRaisesRegex(ValueError, "Movement already exists"):
            self.inventory.register_movement(movement)

    def test_stock_cannot_fall_below_zero(self) -> None:
        with self.assertRaises(StockWouldBecomeNegative) as context:
            self.inventory.register_movement(
                Movement("M-1", "P-1", MovementType.SALE, 1)
            )

        self.assertEqual(context.exception.current_stock, 0)
        self.assertEqual(context.exception.delta, -1)
        self.assertEqual(self.inventory.get_stock("P-1"), 0)
        self.assertEqual(self.inventory.get_movements("P-1"), ())

    def test_movement_cannot_take_positive_stock_below_zero(self) -> None:
        self.inventory.register_movement(
            Movement("M-1", "P-1", MovementType.RECEIPT, 4)
        )

        with self.assertRaises(StockWouldBecomeNegative):
            self.inventory.register_movement(
                Movement("M-2", "P-1", MovementType.SALE, 5)
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
            Movement("M-20", "P-1", MovementType.RECEIPT, 3)
        )

        movements = self.inventory.record_sale(
            "SALE-1", (Scan("S-22", "P-1"), Scan("S-23", "P-1")), "checkout-2"
        )

        self.assertEqual(movements[0].movement_type, MovementType.SALE)
        self.assertEqual(movements[0].quantity, 2)
        self.assertEqual(self.inventory.get_stock("P-1"), 1)

    def test_checkout_sale_that_exceeds_stock_locks_terminal(self) -> None:
        self.inventory.register_movement(
            Movement("M-21", "P-1", MovementType.RECEIPT, 1)
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
            Movement("M-22", "P-1", MovementType.RECEIPT, 8)
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

        with self.assertRaises(StockWouldBecomeNegative):
            self.inventory.register_movement(
                Movement("M-23", "P-1", MovementType.SALE, 1), "manual-terminal"
            )

        self.assertTrue(self.inventory.is_terminal_locked("manual-terminal"))
        self.assertFalse(
            self.inventory.authorize_manager("manual-terminal", "manager", "wrong")
        )
        with self.assertRaises(TerminalLockedError):
            self.inventory.register_movement(
                Movement("M-24", "P-1", MovementType.RECEIPT, 1), "manual-terminal"
            )

        self.assertTrue(
            self.inventory.authorize_manager("manual-terminal", "manager", "valid")
        )
        self.assertFalse(self.inventory.is_terminal_locked("manual-terminal"))
        self.inventory.register_movement(
            Movement("M-25", "P-1", MovementType.RECEIPT, 2), "manual-terminal"
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
        with self.assertRaisesRegex(sqlite3.IntegrityError, "stock cannot be negative"):
            connection.execute(
                """INSERT INTO movements
                   (movement_id, product_id, movement_type, quantity)
                   VALUES (?, ?, ?, ?)""",
                ("M-DB-1", "P-DB", "sale", 1),
            )

        connection.execute(
            """INSERT INTO movements
               (movement_id, product_id, movement_type, quantity)
               VALUES (?, ?, ?, ?)""",
            ("M-DB-2", "P-DB", "receipt", 3),
        )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "stock cannot be negative"):
            connection.execute(
                """INSERT INTO movements
                   (movement_id, product_id, movement_type, quantity)
                   VALUES (?, ?, ?, ?)""",
                ("M-DB-3", "P-DB", "sale", 4),
            )
        stock = connection.execute(
            "SELECT stock FROM product_stock WHERE product_id = ?", ("P-DB",)
        ).fetchone()[0]
        self.assertEqual(stock, 3)
        connection.close()


if __name__ == "__main__":
    unittest.main()
