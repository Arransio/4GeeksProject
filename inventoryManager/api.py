"""Small standard-library WSGI API for the inventory-manager sketch."""

import json
from typing import Any, Callable, Iterable

from inventory import (
    InventoryService,
    InvoiceLine,
    InvoiceValidationError,
    Scan,
    SupplierInvoice,
)


class InventoryAPI:
    """Expose invoice receiving as ``POST /invoices/receive``."""

    def __init__(self, inventory: InventoryService) -> None:
        self.inventory = inventory

    def __call__(
        self, environ: dict[str, Any], start_response: Callable[..., Any]
    ) -> Iterable[bytes]:
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "")
        if method != "POST" or path != "/invoices/receive":
            return self._respond(start_response, "404 Not Found", {"error": "Not found"})

        try:
            content_length = int(environ.get("CONTENT_LENGTH") or 0)
            if content_length <= 0:
                raise ValueError("Request body is required")
            body = environ["wsgi.input"].read(content_length)
            payload = json.loads(body)
            invoice, scans = self._parse_invoice_request(payload)
            movements = self.inventory.receive_invoice(invoice, scans)
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError, ValueError) as exc:
            return self._respond(start_response, "400 Bad Request", {"error": str(exc)})

        return self._respond(
            start_response,
            "201 Created",
            {
                "invoice_id": invoice.invoice_id,
                "movements": [
                    {
                        "movement_id": movement.movement_id,
                        "product_id": movement.product_id,
                        "quantity": movement.quantity,
                        "type": movement.movement_type.value,
                    }
                    for movement in movements
                ],
            },
        )

    @staticmethod
    def _parse_invoice_request(payload: Any) -> tuple[SupplierInvoice, tuple[Scan, ...]]:
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object")
        invoice_data = payload.get("invoice")
        scan_data = payload.get("scans")
        if not isinstance(invoice_data, dict) or not isinstance(scan_data, list):
            raise ValueError("Expected 'invoice' object and 'scans' array")

        raw_lines = invoice_data.get("lines")
        if not isinstance(raw_lines, list):
            raise ValueError("Invoice 'lines' must be an array")
        try:
            lines = tuple(
                InvoiceLine(
                    product_id=line["product_id"],
                    quantity=line["quantity"],
                )
                for line in raw_lines
            )
            scans = tuple(
                Scan(
                    scan_id=scan["scan_id"],
                    product_id=scan["product_id"],
                    item_count=scan.get("item_count", 1),
                )
                for scan in scan_data
            )
            invoice_id = invoice_data["invoice_id"]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Malformed invoice or scan data: {exc}") from exc
        if not isinstance(invoice_id, str):
            raise ValueError("Invoice ID must be a string")
        return SupplierInvoice(invoice_id=invoice_id, lines=lines), scans

    @staticmethod
    def _respond(
        start_response: Callable[..., Any], status: str, payload: dict[str, Any]
    ) -> list[bytes]:
        body = json.dumps(payload).encode("utf-8")
        start_response(
            status,
            [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(body))),
            ],
        )
        return [body]


def create_app(inventory: InventoryService) -> InventoryAPI:
    """Factory for use with any WSGI server."""
    return InventoryAPI(inventory)
