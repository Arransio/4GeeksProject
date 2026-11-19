"""Run the inventory API locally."""

from __future__ import annotations

import os

import uvicorn

from inventory import InventoryService
from api import create_app


def main() -> None:
    database_path = os.environ.get("INVENTORY_DATABASE", "inventory.sqlite3")
    host = os.environ.get("INVENTORY_HOST", "127.0.0.1")
    port = int(os.environ.get("INVENTORY_PORT", "8766"))
    inventory = InventoryService(database_path=database_path)
    try:
        uvicorn.run(create_app(inventory), host=host, port=port)
    finally:
        inventory.close()


if __name__ == "__main__":
    main()