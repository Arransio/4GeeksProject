"""FastAPI endpoints for HealthCore clinic inventory."""

from __future__ import annotations

import sqlite3
from decimal import Decimal
from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import JSONResponse

from inventory import (
    InventoryReconciliation,
    InventoryService,
    InvoiceLine,
    Movement,
    MovementType,
    Product,
    Scan,
    SupplierInvoice,
)


class ProductCreate(BaseModel):
    product_id: str
    name: str
    unit: str
    reorder_point: int


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    unit: Optional[str] = None
    reorder_point: Optional[int] = None


class MovementCreate(BaseModel):
    movement_id: str
    product_id: str
    lot_id: str
    movement_type: MovementType
    quantity: int
    reason: str
    unit_cost: Optional[Decimal] = None
    reference_id: Optional[str] = None


class InvoiceLineRequest(BaseModel):
    product_id: str
    quantity: int
    unit_cost: Optional[Decimal] = None


class ScanRequest(BaseModel):
    scan_id: str
    product_id: str
    item_count: int = 1


class InvoiceRequest(BaseModel):
    invoice_id: str
    lines: List[InvoiceLineRequest]
    scans: List[ScanRequest]


def _product_payload(service: InventoryService, product_id: str) -> dict:
    product = service.get_product(product_id)
    return {
        "product_id": product.product_id,
        "name": product.name,
        "unit": product.unit,
        "reorder_point": product.reorder_point,
    }


def _movement_payload(movement: Movement) -> dict:
    return {
        "movement_id": movement.movement_id,
        "product_id": movement.product_id,
        "lot_id": movement.lot_id,
        "movement_type": movement.movement_type.value,
        "quantity": movement.quantity,
        "unit_cost": str(movement.unit_cost) if movement.unit_cost is not None else None,
        "reference_id": movement.reference_id,
        "reason": movement.reason,
        "occurred_at": movement.occurred_at,
    }


def create_app(inventory: InventoryService) -> FastAPI:
    app = FastAPI(title="HealthCore Inventory API", version="1.0.0")
    app.state.inventory = inventory

    @app.exception_handler(ValueError)
    async def inventory_error_handler(request, error: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(error)})

    @app.exception_handler(sqlite3.IntegrityError)
    async def database_error_handler(request, error: sqlite3.IntegrityError):
        return JSONResponse(status_code=400, content={"detail": str(error)})

    @app.post("/api/products", status_code=201)
    def create_product(payload: ProductCreate) -> dict:
        inventory.add_product(Product(**payload.dict()))
        return _product_payload(inventory, payload.product_id)

    @app.get("/api/products")
    def list_products() -> list:
        return [_product_payload(inventory, product.product_id) for product in inventory.list_products()]

    @app.get("/api/products/{product_id}")
    def get_product(product_id: str) -> dict:
        return _product_payload(inventory, product_id)

    @app.patch("/api/products/{product_id}")
    def update_product(product_id: str, payload: ProductUpdate) -> dict:
        product = inventory.update_product(
            product_id,
            **{key: value for key, value in payload.dict().items() if value is not None},
        )
        return {
            "product_id": product.product_id,
            "name": product.name,
            "unit": product.unit,
            "reorder_point": product.reorder_point,
        }

    @app.get("/api/inventory")
    def list_inventory() -> list:
        return list(inventory.list_inventory())

    @app.get("/api/inventory/low-stock")
    def list_low_stock() -> list:
        return list(inventory.get_low_stock_products())

    @app.get("/api/products/{product_id}/lots")
    def list_lots(product_id: str) -> list:
        return [lot.__dict__ for lot in inventory.list_lots(product_id)]

    @app.get("/api/products/{product_id}/movements")
    def list_movements(product_id: str) -> list:
        return [_movement_payload(movement) for movement in inventory.get_movements(product_id)]

    @app.post("/api/movements", status_code=201)
    def create_movement(payload: MovementCreate) -> dict:
        movement = Movement(**payload.dict())
        inventory.register_movement(movement)
        return _movement_payload(inventory.get_movements(movement.product_id)[-1])

    @app.post("/api/invoices/receive", status_code=201)
    def receive_invoice(payload: InvoiceRequest) -> dict:
        invoice = SupplierInvoice(
            payload.invoice_id,
            tuple(
                InvoiceLine(line.product_id, line.quantity, line.unit_cost)
                for line in payload.lines
            ),
        )
        scans = tuple(
            Scan(scan.scan_id, scan.product_id, scan.item_count) for scan in payload.scans
        )
        movements = inventory.receive_invoice(invoice, scans)
        return {
            "invoice_id": invoice.invoice_id,
            "movements": [_movement_payload(movement) for movement in movements],
        }

    @app.post("/api/inventory/reconcile", status_code=201)
    def reconcile_inventory(payload: dict) -> list:
        reconciliation = InventoryReconciliation(
            payload["reconciliation_id"], payload["actual_counts"]
        )
        movements = inventory.reconcile_month_end(reconciliation)
        return [_movement_payload(movement) for movement in movements]

    return app