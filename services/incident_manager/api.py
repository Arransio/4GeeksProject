"""FastAPI application for the incident manager and static backoffice."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Body, FastAPI, Header, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from services.incident_manager.service import (
    IncidentCatalogs,
    IncidentNotFound,
    IncidentService,
    InvalidIncident,
)


class CreateIncidentRequest(BaseModel):
    title: str
    description: str
    incident_type: str
    severity: str
    channel: str
    responsible_area: str


def load_catalogs(path: str | Path) -> IncidentCatalogs:
    """Load approved domain catalogs from an operator-provided JSON file."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    catalogs = IncidentCatalogs(
        incident_types=tuple(raw["incident_types"]),
        severities=tuple(raw["severities"]),
        channels=tuple(raw["channels"]),
        areas=tuple(raw["areas"]),
        statuses=tuple(raw["statuses"]),
        closed_statuses=tuple(raw["closed_statuses"]),
        initial_status=raw["initial_status"],
        transitions={key: tuple(value) for key, value in raw["transitions"].items()},
    )
    catalogs.validate()
    return catalogs


def _actor(value: str) -> str:
    value = value.strip()
    if not value:
        raise InvalidIncident("Actor is required")
    return value


def create_app(
    service: IncidentService, static_dir: str | Path | None = None
) -> FastAPI:
    """Create the HTTP API around an injected incident service."""
    if static_dir is None:
        static_dir = Path(__file__).resolve().parents[2] / "uis/backoffice/incidents"
    app = FastAPI(title="HealthCore Incident Manager", version="1.0.0")
    app.state.incident_service = service

    @app.exception_handler(IncidentNotFound)
    async def incident_not_found_handler(
        request: Request, error: IncidentNotFound
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"error": str(error)})

    @app.exception_handler(InvalidIncident)
    async def invalid_incident_handler(
        request: Request, error: InvalidIncident
    ) -> JSONResponse:
        return JSONResponse(status_code=400, content={"error": str(error)})

    @app.get("/api/catalogs")
    def get_catalogs() -> Dict[str, Any]:
        return service.catalogs.as_dict()

    @app.get("/api/summary/open-by-severity")
    def get_open_summary() -> Dict[str, int]:
        return service.open_incidents_by_severity()

    @app.get("/api/incidents")
    def list_incidents(
        status: Optional[str] = Query(default=None),
        severity: Optional[str] = Query(default=None),
        responsible_area: Optional[str] = Query(default=None),
    ) -> list:
        return service.list_incidents(
            status=status, severity=severity, responsible_area=responsible_area
        )

    @app.post("/api/incidents", status_code=201)
    def create_incident(
        payload: CreateIncidentRequest, x_actor: str = Header(...)
    ) -> Dict[str, str]:
        return service.create_incident(
            title=payload.title,
            description=payload.description,
            incident_type=payload.incident_type,
            severity=payload.severity,
            channel=payload.channel,
            responsible_area=payload.responsible_area,
            actor=_actor(x_actor),
        )

    @app.get("/api/incidents/{incident_id}/history")
    def get_incident_history(incident_id: str) -> list:
        return service.get_history(incident_id)

    @app.get("/api/incidents/{incident_id}")
    def get_incident(incident_id: str) -> Dict[str, str]:
        return service.get_incident(incident_id)

    @app.patch("/api/incidents/{incident_id}")
    def update_incident(
        incident_id: str,
        payload: Dict[str, Any] = Body(...),
        x_actor: str = Header(...),
    ) -> Dict[str, str]:
        actor = _actor(x_actor)
        if "status" in payload:
            if set(payload) != {"status"}:
                raise InvalidIncident("Change status separately from other fields")
            return service.transition_incident(
                incident_id, status=payload["status"], actor=actor
            )
        if "responsible_area" in payload:
            if set(payload) != {"responsible_area"}:
                raise InvalidIncident("Change responsibility separately from other fields")
            return service.assign_incident(
                incident_id,
                responsible_area=payload["responsible_area"],
                actor=actor,
            )
        return service.update_incident(incident_id, actor=actor, **payload)

    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="backoffice")
    return app
