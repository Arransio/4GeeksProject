"""SQLite-backed incident domain service with an append-only audit log."""

from __future__ import annotations

import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


class IncidentNotFound(LookupError):
    """Raised when an incident identifier does not exist."""


class InvalidIncident(ValueError):
    """Raised when incident data or a state transition is invalid."""


@dataclass(frozen=True)
class IncidentCatalogs:
    incident_types: tuple[str, ...]
    severities: tuple[str, ...]
    channels: tuple[str, ...]
    areas: tuple[str, ...]
    statuses: tuple[str, ...]
    closed_statuses: tuple[str, ...]
    initial_status: str
    transitions: dict[str, tuple[str, ...]]

    def validate(self) -> None:
        values = {
            "incident_types": self.incident_types,
            "severities": self.severities,
            "channels": self.channels,
            "areas": self.areas,
            "statuses": self.statuses,
        }
        for catalog_name, catalog_values in values.items():
            if not catalog_values or any(not item for item in catalog_values):
                raise ValueError(f"Catalog '{catalog_name}' must contain values")
            if len(set(catalog_values)) != len(catalog_values):
                raise ValueError(f"Catalog '{catalog_name}' contains duplicates")
        if self.initial_status not in self.statuses:
            raise ValueError("Initial status must belong to the status catalog")
        if not self.closed_statuses or not set(self.closed_statuses).issubset(self.statuses):
            raise ValueError("Closed statuses must be a non-empty subset of statuses")
        if self.initial_status in self.closed_statuses:
            raise ValueError("Initial status cannot be closed")
        if set(self.transitions) - set(self.statuses):
            raise ValueError("Transition source is not in the status catalog")
        if any(
            destination not in self.statuses
            for destinations in self.transitions.values()
            for destination in destinations
        ):
            raise ValueError("Transition destination is not in the status catalog")

    def as_dict(self) -> dict[str, Any]:
        return {
            "incident_types": list(self.incident_types),
            "severities": list(self.severities),
            "channels": list(self.channels),
            "areas": list(self.areas),
            "statuses": list(self.statuses),
            "closed_statuses": list(self.closed_statuses),
            "initial_status": self.initial_status,
            "transitions": {
                status: list(destinations)
                for status, destinations in self.transitions.items()
            },
        }


class IncidentService:
    """Manage incidents and audit all responsibility and status changes."""

    def __init__(self, database_path: str, catalogs: IncidentCatalogs) -> None:
        catalogs.validate()
        self.catalogs = catalogs
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._create_schema()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.executescript(
                """
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    incident_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    responsible_area TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS incident_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL REFERENCES incidents(incident_id),
                    event_type TEXT NOT NULL,
                    field_name TEXT,
                    old_value TEXT,
                    new_value TEXT,
                    actor TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS incident_events_timeline
                    ON incident_events(incident_id, event_id);
                CREATE TRIGGER IF NOT EXISTS incident_events_no_update
                BEFORE UPDATE ON incident_events
                BEGIN
                    SELECT RAISE(ABORT, 'incident audit events are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS incident_events_no_delete
                BEFORE DELETE ON incident_events
                BEGIN
                    SELECT RAISE(ABORT, 'incident audit events are immutable');
                END;
                """
            )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _require_text(field_name: str, value: str, actor: bool = False) -> str:
        if not isinstance(value, str) or not value.strip():
            label = "Actor" if actor else field_name.replace("_", " ").capitalize()
            raise InvalidIncident(f"{label} is required")
        return value.strip()

    @staticmethod
    def _require_catalog_value(field_name: str, value: str, choices: tuple[str, ...]) -> str:
        if value not in choices:
            raise InvalidIncident(f"Unsupported {field_name}: {value}")
        return value

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, str]:
        return dict(row)

    def _event(
        self,
        incident_id: str,
        event_type: str,
        actor: str,
        occurred_at: str,
        field_name: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
    ) -> None:
        self._connection.execute(
            """INSERT INTO incident_events
               (incident_id, event_type, field_name, old_value, new_value, actor, occurred_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (incident_id, event_type, field_name, old_value, new_value, actor, occurred_at),
        )

    def create_incident(
        self,
        *,
        title: str,
        description: str,
        incident_type: str,
        severity: str,
        channel: str,
        responsible_area: str,
        actor: str,
    ) -> dict[str, str]:
        values = {
            "title": self._require_text("title", title),
            "description": self._require_text("description", description),
            "incident_type": self._require_catalog_value(
                "incident type", incident_type, self.catalogs.incident_types
            ),
            "severity": self._require_catalog_value(
                "severity", severity, self.catalogs.severities
            ),
            "channel": self._require_catalog_value("channel", channel, self.catalogs.channels),
            "responsible_area": self._require_catalog_value(
                "responsible area", responsible_area, self.catalogs.areas
            ),
        }
        actor = self._require_text("actor", actor, actor=True)
        incident_id = f"INC-{uuid.uuid4().hex[:12].upper()}"
        occurred_at = self._timestamp()
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO incidents
                   (incident_id, title, description, incident_type, severity, channel,
                    responsible_area, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    incident_id,
                    values["title"],
                    values["description"],
                    values["incident_type"],
                    values["severity"],
                    values["channel"],
                    values["responsible_area"],
                    self.catalogs.initial_status,
                    occurred_at,
                    occurred_at,
                ),
            )
            self._event(incident_id, "created", actor, occurred_at)
        return self.get_incident(incident_id)

    def get_incident(self, incident_id: str) -> dict[str, str]:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)
            ).fetchone()
        if row is None:
            raise IncidentNotFound(incident_id)
        return self._row_to_dict(row)

    def list_incidents(
        self,
        *,
        status: str | None = None,
        severity: str | None = None,
        responsible_area: str | None = None,
    ) -> list[dict[str, str]]:
        filters = {
            "status": (status, self.catalogs.statuses),
            "severity": (severity, self.catalogs.severities),
            "responsible_area": (responsible_area, self.catalogs.areas),
        }
        where: list[str] = []
        parameters: list[str] = []
        for field_name, (value, choices) in filters.items():
            if value is not None:
                self._require_catalog_value(field_name, value, choices)
                where.append(f"{field_name} = ?")
                parameters.append(value)
        query = "SELECT * FROM incidents"
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY created_at DESC, incident_id DESC"
        with self._lock:
            rows = self._connection.execute(query, parameters).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def update_incident(self, incident_id: str, *, actor: str, **changes: str) -> dict[str, str]:
        editable = {"title", "description", "incident_type", "severity", "channel"}
        if not changes or set(changes) - editable:
            raise InvalidIncident("Only title, description, type, severity, and channel are editable")
        actor = self._require_text("actor", actor, actor=True)
        for field_name in ("title", "description"):
            if field_name in changes:
                changes[field_name] = self._require_text(field_name, changes[field_name])
        catalog_fields = {
            "incident_type": self.catalogs.incident_types,
            "severity": self.catalogs.severities,
            "channel": self.catalogs.channels,
        }
        for field_name, choices in catalog_fields.items():
            if field_name in changes:
                self._require_catalog_value(field_name, changes[field_name], choices)
        with self._lock, self._connection:
            incident = self._get_row(incident_id)
            occurred_at = self._timestamp()
            for field_name, new_value in changes.items():
                old_value = incident[field_name]
                if old_value == new_value:
                    continue
                self._connection.execute(
                    f"UPDATE incidents SET {field_name} = ?, updated_at = ? WHERE incident_id = ?",
                    (new_value, occurred_at, incident_id),
                )
                self._event(
                    incident_id,
                    "field_changed",
                    actor,
                    occurred_at,
                    field_name,
                    old_value,
                    new_value,
                )
        return self.get_incident(incident_id)

    def assign_incident(self, incident_id: str, *, responsible_area: str, actor: str) -> dict[str, str]:
        self._require_catalog_value("responsible area", responsible_area, self.catalogs.areas)
        actor = self._require_text("actor", actor, actor=True)
        with self._lock, self._connection:
            incident = self._get_row(incident_id)
            old_value = incident["responsible_area"]
            if old_value != responsible_area:
                occurred_at = self._timestamp()
                self._connection.execute(
                    "UPDATE incidents SET responsible_area = ?, updated_at = ? WHERE incident_id = ?",
                    (responsible_area, occurred_at, incident_id),
                )
                self._event(
                    incident_id,
                    "responsibility_changed",
                    actor,
                    occurred_at,
                    "responsible_area",
                    old_value,
                    responsible_area,
                )
        return self.get_incident(incident_id)

    def transition_incident(
        self, incident_id: str, *, status: str, actor: str
    ) -> dict[str, str]:
        self._require_catalog_value("status", status, self.catalogs.statuses)
        actor = self._require_text("actor", actor, actor=True)
        with self._lock, self._connection:
            incident = self._get_row(incident_id)
            old_status = incident["status"]
            if status not in self.catalogs.transitions.get(old_status, ()):
                raise InvalidIncident(f"Transition not allowed: {old_status} -> {status}")
            occurred_at = self._timestamp()
            self._connection.execute(
                "UPDATE incidents SET status = ?, updated_at = ? WHERE incident_id = ?",
                (status, occurred_at, incident_id),
            )
            self._event(
                incident_id,
                "status_changed",
                actor,
                occurred_at,
                "status",
                old_status,
                status,
            )
        return self.get_incident(incident_id)

    def get_history(self, incident_id: str) -> list[dict[str, Any]]:
        self.get_incident(incident_id)
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM incident_events WHERE incident_id = ? ORDER BY event_id",
                (incident_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def open_incidents_by_severity(self) -> dict[str, int]:
        terminal_statuses = {
            status for status in self.catalogs.closed_statuses
        }
        active_statuses = [
            status for status in self.catalogs.statuses if status not in terminal_statuses
        ]
        result = {severity: 0 for severity in self.catalogs.severities}
        if not active_statuses:
            return result
        placeholders = ", ".join("?" for _ in active_statuses)
        with self._lock:
            rows = self._connection.execute(
                f"""SELECT severity, COUNT(*) AS count FROM incidents
                    WHERE status IN ({placeholders}) GROUP BY severity""",
                active_statuses,
            ).fetchall()
        result.update({row["severity"]: row["count"] for row in rows})
        return result

    def _get_row(self, incident_id: str) -> sqlite3.Row:
        row = self._connection.execute(
            "SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)
        ).fetchone()
        if row is None:
            raise IncidentNotFound(incident_id)
        return row