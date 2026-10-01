"""Inventory domain logic: stock is derived exclusively from movements."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Callable


class MovementType(str, Enum):
    """Supported inventory movements and their effect on stock."""

    RECEIPT = "receipt"
    RETURN = "return"
    SALE = "sale"
    SHRINKAGE = "shrinkage"
    INVENTORY_GAIN = "inventory_gain"

    @property
    def sign(self) -> int:
        return 1 if self in (
            MovementType.RECEIPT,
            MovementType.RETURN,
            MovementType.INVENTORY_GAIN,
        ) else -1


@dataclass(frozen=True)
class Product:
    """Product identity; deliberately contains no stored or editable stock."""

    product_id: str
    name: str


@dataclass(frozen=True)
class Movement:
    """Immutable record of one inventory operation."""

    movement_id: str
    product_id: str
    movement_type: MovementType
    quantity: int
    unit_cost: Decimal | None = None
    reference_id: str | None = None

    @property
    def stock_delta(self) -> int:
        return self.movement_type.sign * self.quantity


class StockWouldBecomeNegative(ValueError):
    """Raised when a movement would take a product below the stock minimum."""

    def __init__(self, product_id: str, current_stock: int, delta: int) -> None:
        self.product_id = product_id
        self.current_stock = current_stock
        self.delta = delta
        super().__init__(
            f"Movement would make stock negative for {product_id}: "
            f"{current_stock} + ({delta}) < 0"
        )


class InvalidScan(ValueError):
    """Raised when one scan does not unambiguously represent one item."""


class TerminalLockedError(RuntimeError):
    """Raised when a locked terminal attempts another inventory operation."""


@dataclass(frozen=True)
class Scan:
    """One scanner reading, which must resolve to exactly one product item."""

    scan_id: str
    product_id: str
    item_count: int = 1


@dataclass(frozen=True)
class InvoiceLine:
    """An invoice's expected quantity and unit cost for one product."""

    product_id: str
    quantity: int
    unit_cost: Decimal | None = None


@dataclass(frozen=True)
class SupplierInvoice:
    """Invoice data decoded from the supplier document scan."""

    invoice_id: str
    lines: tuple[InvoiceLine, ...]


class InvoiceValidationError(ValueError):
    """Raised when invoice data and the received item scans do not match."""


@dataclass(frozen=True)
class InventoryReconciliation:
    """Physical item counts captured during a monthly stocktake."""

    reconciliation_id: str
    actual_counts: dict[str, int]


class InventoryService:
    """Minimal in-memory backend for inventory movements and workflows."""

    def __init__(
        self,
        manager_credential_verifier: Callable[[str, str], bool] | None = None,
    ) -> None:
        self._products: dict[str, Product] = {}
        self._movements: list[Movement] = []
        self._movement_ids: set[str] = set()
        self._scan_ids: set[str] = set()
        self._invoice_ids: set[str] = set()
        self._operation_ids: set[str] = set()
        self._reconciliation_ids: set[str] = set()
        self._locked_terminals: set[str] = set()
        self._lock_reasons: dict[str, StockWouldBecomeNegative] = {}
        self._manager_credential_verifier = manager_credential_verifier

    def add_product(self, product: Product) -> None:
        if product.product_id in self._products:
            raise ValueError(f"Product already exists: {product.product_id}")
        self._products[product.product_id] = product

    def _ensure_terminal_unlocked(self, terminal_id: str) -> None:
        if terminal_id in self._locked_terminals:
            raise TerminalLockedError(
                f"Terminal {terminal_id} is locked pending manager review"
            )

    def _commit_movements(
        self, movements: tuple[Movement, ...], terminal_id: str | None = None
    ) -> None:
        """Validate a batch and append atomically to the movement log."""
        seen_movement_ids: set[str] = set()
        stock_changes: dict[str, int] = {}
        for movement in movements:
            if movement.product_id not in self._products:
                raise ValueError(f"Unknown product: {movement.product_id}")
            if movement.movement_id in self._movement_ids or movement.movement_id in seen_movement_ids:
                raise ValueError(f"Movement already exists: {movement.movement_id}")
            if type(movement.quantity) is not int or movement.quantity <= 0:
                raise ValueError("Movement quantity must be a positive integer")
            if not isinstance(movement.movement_type, MovementType):
                raise ValueError("Unsupported movement type")
            seen_movement_ids.add(movement.movement_id)
            stock_changes[movement.product_id] = (
                stock_changes.get(movement.product_id, 0) + movement.stock_delta
            )

        for product_id, delta in stock_changes.items():
            current_stock = self.get_stock(product_id)
            if current_stock + delta < 0:
                error = StockWouldBecomeNegative(product_id, current_stock, delta)
                if terminal_id is not None:
                    self._locked_terminals.add(terminal_id)
                    self._lock_reasons[terminal_id] = error
                raise error

        self._movements.extend(movements)
        self._movement_ids.update(seen_movement_ids)

    def register_movement(self, movement: Movement, terminal_id: str = "default") -> None:
        """Manually register one movement, locking its terminal on negative stock."""
        self._ensure_terminal_unlocked(terminal_id)
        self._commit_movements((movement,), terminal_id)

    def is_terminal_locked(self, terminal_id: str) -> bool:
        return terminal_id in self._locked_terminals

    def get_terminal_lock_reason(
        self, terminal_id: str
    ) -> StockWouldBecomeNegative | None:
        return self._lock_reasons.get(terminal_id)

    def authorize_manager(self, terminal_id: str, username: str, password: str) -> bool:
        """Unlock following manager review via injected credential verifier.

        Credentials are delegated to the verifier and are never persisted here.
        If no authentication integration is configured, the terminal remains
        locked. Production code must connect this callback to secure auth.
        """
        if terminal_id not in self._locked_terminals:
            return False
        if self._manager_credential_verifier is None:
            return False
        if not self._manager_credential_verifier(username, password):
            return False
        self._locked_terminals.remove(terminal_id)
        self._lock_reasons.pop(terminal_id, None)
        return True

    def _record_scanned_operation(
        self,
        operation_id: str,
        scans: tuple[Scan, ...],
        movement_type: MovementType,
        terminal_id: str,
    ) -> tuple[Movement, ...]:
        self._ensure_terminal_unlocked(terminal_id)
        if not operation_id:
            raise ValueError("Operation identifier must not be empty")
        if operation_id in self._operation_ids:
            raise ValueError(f"Operation already processed: {operation_id}")
        if not scans:
            raise ValueError("At least one item scan is required")

        scan_ids: set[str] = set()
        counts: dict[str, int] = {}
        for scan in scans:
            if type(scan.item_count) is not int or scan.item_count != 1:
                raise InvalidScan("A scan must represent exactly one item")
            if not scan.scan_id or scan.scan_id in self._scan_ids or scan.scan_id in scan_ids:
                raise InvalidScan(f"Missing or previously processed scan: {scan.scan_id}")
            if scan.product_id not in self._products:
                raise InvalidScan(f"Scan references unknown product: {scan.product_id}")
            scan_ids.add(scan.scan_id)
            counts[scan.product_id] = counts.get(scan.product_id, 0) + 1

        movements = tuple(
            Movement(
                movement_id=f"{movement_type.value}:{operation_id}:{product_id}",
                product_id=product_id,
                movement_type=movement_type,
                quantity=quantity,
                reference_id=operation_id,
            )
            for product_id, quantity in counts.items()
        )
        self._commit_movements(movements, terminal_id)
        self._scan_ids.update(scan_ids)
        self._operation_ids.add(operation_id)
        return movements

    def record_return(
        self, operation_id: str, scans: tuple[Scan, ...], terminal_id: str = "default"
    ) -> tuple[Movement, ...]:
        """Register scanned returned items as stock-increasing movements."""
        return self._record_scanned_operation(
            operation_id, scans, MovementType.RETURN, terminal_id
        )

    def record_sale(
        self, operation_id: str, scans: tuple[Scan, ...], terminal_id: str = "default"
    ) -> tuple[Movement, ...]:
        """Register scanned checkout items, reducing stock automatically."""
        return self._record_scanned_operation(
            operation_id, scans, MovementType.SALE, terminal_id
        )

    def validate_scan(self, scan: Scan) -> None:
        """Validate and record a unique scan representing exactly one item."""
        if type(scan.item_count) is not int or scan.item_count != 1:
            raise InvalidScan("A scan must represent exactly one item")
        if scan.product_id not in self._products:
            raise InvalidScan(f"Scan references unknown product: {scan.product_id}")
        if not scan.scan_id:
            raise InvalidScan("Scan identifier must not be empty")
        if scan.scan_id in self._scan_ids:
            raise InvalidScan(f"Scan already processed: {scan.scan_id}")
        self._scan_ids.add(scan.scan_id)

    def receive_invoice(
        self, invoice: SupplierInvoice, item_scans: tuple[Scan, ...]
    ) -> tuple[Movement, ...]:
        """Verify invoice quantities against individual scans, then receive."""
        if not invoice.invoice_id:
            raise InvoiceValidationError("Invoice identifier must not be empty")
        if invoice.invoice_id in self._invoice_ids:
            raise InvoiceValidationError(
                f"Invoice already processed: {invoice.invoice_id}"
            )
        if not invoice.lines:
            raise InvoiceValidationError("Invoice must contain at least one line")

        expected: dict[str, InvoiceLine] = {}
        for line in invoice.lines:
            if line.product_id not in self._products:
                raise InvoiceValidationError(
                    f"Invoice references unknown product: {line.product_id}"
                )
            if type(line.quantity) is not int or line.quantity <= 0:
                raise InvoiceValidationError(
                    f"Invoice quantity must be a positive integer: {line.product_id}"
                )
            if line.product_id in expected:
                raise InvoiceValidationError(
                    f"Duplicate invoice line for product: {line.product_id}"
                )
            expected[line.product_id] = line

        scanned: dict[str, int] = {product_id: 0 for product_id in expected}
        batch_scan_ids: set[str] = set()
        for scan in item_scans:
            if type(scan.item_count) is not int or scan.item_count != 1:
                raise InvoiceValidationError(
                    "Each item scan must represent exactly one item"
                )
            if not scan.scan_id or scan.scan_id in self._scan_ids:
                raise InvoiceValidationError(
                    f"Missing or previously processed scan: {scan.scan_id}"
                )
            if scan.scan_id in batch_scan_ids:
                raise InvoiceValidationError(f"Duplicate scan in invoice: {scan.scan_id}")
            if scan.product_id not in expected:
                raise InvoiceValidationError(
                    f"Scanned product is not listed on invoice: {scan.product_id}"
                )
            batch_scan_ids.add(scan.scan_id)
            scanned[scan.product_id] += 1

        mismatches = [
            f"{product_id}: invoice={line.quantity}, scanned={scanned[product_id]}"
            for product_id, line in expected.items()
            if scanned[product_id] != line.quantity
        ]
        if mismatches:
            raise InvoiceValidationError(
                "Scanned quantities do not match invoice (" + "; ".join(mismatches) + ")"
            )

        movements = tuple(
            Movement(
                movement_id=f"invoice:{invoice.invoice_id}:line:{index}",
                product_id=line.product_id,
                movement_type=MovementType.RECEIPT,
                quantity=line.quantity,
                unit_cost=line.unit_cost,
                reference_id=invoice.invoice_id,
            )
            for index, line in enumerate(invoice.lines, start=1)
        )
        self._commit_movements(movements)
        self._scan_ids.update(batch_scan_ids)
        self._invoice_ids.add(invoice.invoice_id)
        return movements

    def reconcile_month_end(
        self, reconciliation: InventoryReconciliation
    ) -> tuple[Movement, ...]:
        """Compare physical counts and record discrepancies as movements."""
        if not reconciliation.reconciliation_id:
            raise ValueError("Reconciliation identifier must not be empty")
        if reconciliation.reconciliation_id in self._reconciliation_ids:
            raise ValueError(
                f"Reconciliation already processed: {reconciliation.reconciliation_id}"
            )
        if set(reconciliation.actual_counts) != set(self._products):
            raise ValueError("Reconciliation must include every known product exactly once")

        movements: list[Movement] = []
        for product_id, actual in reconciliation.actual_counts.items():
            if type(actual) is not int or actual < 0:
                raise ValueError(f"Actual count must be a non-negative integer: {product_id}")
            difference = actual - self.get_stock(product_id)
            if difference == 0:
                continue
            movement_type = (
                MovementType.SHRINKAGE if difference < 0 else MovementType.INVENTORY_GAIN
            )
            movements.append(
                Movement(
                    movement_id=f"stocktake:{reconciliation.reconciliation_id}:{product_id}",
                    product_id=product_id,
                    movement_type=movement_type,
                    quantity=abs(difference),
                    reference_id=reconciliation.reconciliation_id,
                )
            )
        self._commit_movements(tuple(movements))
        self._reconciliation_ids.add(reconciliation.reconciliation_id)
        return tuple(movements)

    def get_stock(self, product_id: str) -> int:
        if product_id not in self._products:
            raise ValueError(f"Unknown product: {product_id}")
        return sum(
            movement.stock_delta
            for movement in self._movements
            if movement.product_id == product_id
        )

    def get_movements(self, product_id: str) -> tuple[Movement, ...]:
        if product_id not in self._products:
            raise ValueError(f"Unknown product: {product_id}")
        return tuple(
            movement
            for movement in self._movements
            if movement.product_id == product_id
        )
