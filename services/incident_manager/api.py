"""Dependency-free WSGI API and static UI for the incident manager."""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import parse_qs

from services.incident_manager.service import (
    IncidentCatalogs,
    IncidentNotFound,
    IncidentService,
    InvalidIncident,
)


class IncidentAPI:
    def __init__(self, service: IncidentService, static_dir: Path) -> None:
        self.service = service
        self.static_dir = static_dir.resolve()

    def __call__(
        self, environ: dict[str, Any], start_response: Callable[..., Any]
    ) -> Iterable[bytes]:
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")
        if path.startswith("/api/"):
            try:
                payload, status = self._dispatch_api(method, path, environ)
            except IncidentNotFound as error:
                payload, status = {"error": str(error)}, "404 Not Found"
            except InvalidIncident as error:
                payload, status = {"error": str(error)}, "400 Bad Request"
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError, ValueError) as error:
                payload, status = {"error": str(error)}, "400 Bad Request"
            return self._respond_json(start_response, status, payload)
        return self._serve_static(method, path, start_response)

    def _dispatch_api(
        self, method: str, path: str, environ: dict[str, Any]
    ) -> tuple[dict[str, Any] | list[dict[str, Any]], str]:
        if method == "GET" and path == "/api/catalogs":
            return self.service.catalogs.as_dict(), "200 OK"
        if method == "GET" and path == "/api/summary/open-by-severity":
            return self.service.open_incidents_by_severity(), "200 OK"
        if path == "/api/incidents" and method == "GET":
            query = parse_qs(environ.get("QUERY_STRING", ""))
            filters = {
                key: query[key][0]
                for key in ("status", "severity", "responsible_area")
                if key in query
            }
            return self.service.list_incidents(**filters), "200 OK"
        if path == "/api/incidents" and method == "POST":
            data = self._read_json(environ)
            incident = self.service.create_incident(
                title=data.get("title"),
                description=data.get("description"),
                incident_type=data.get("incident_type"),
                severity=data.get("severity"),
                channel=data.get("channel"),
                responsible_area=data.get("responsible_area"),
                actor=self._actor(environ),
            )
            return incident, "201 Created"

        parts = path.strip("/").split("/")
        if len(parts) < 3 or parts[:2] != ["api", "incidents"]:
            return {"error": "Not found"}, "404 Not Found"
        incident_id = parts[2]
        if len(parts) == 4 and parts[3] == "history" and method == "GET":
            return self.service.get_history(incident_id), "200 OK"
        if len(parts) == 3 and method == "GET":
            return self.service.get_incident(incident_id), "200 OK"
        if len(parts) == 3 and method in {"PATCH", "PUT"}:
            data = self._read_json(environ)
            actor = self._actor(environ)
            if "status" in data:
                if set(data) != {"status"}:
                    raise InvalidIncident("Change status separately from other fields")
                return self.service.transition_incident(
                    incident_id, status=data["status"], actor=actor
                ), "200 OK"
            if "responsible_area" in data:
                if set(data) != {"responsible_area"}:
                    raise InvalidIncident("Change responsibility separately from other fields")
                return self.service.assign_incident(
                    incident_id, responsible_area=data["responsible_area"], actor=actor
                ), "200 OK"
            return self.service.update_incident(incident_id, actor=actor, **data), "200 OK"
        return {"error": "Not found"}, "404 Not Found"

    @staticmethod
    def _actor(environ: dict[str, Any]) -> str:
        actor = environ.get("HTTP_X_ACTOR", "").strip()
        if not actor:
            raise InvalidIncident("X-Actor header is required")
        return actor

    @staticmethod
    def _read_json(environ: dict[str, Any]) -> dict[str, Any]:
        content_length = int(environ.get("CONTENT_LENGTH") or 0)
        if content_length <= 0:
            raise ValueError("Request body is required")
        payload = json.loads(environ["wsgi.input"].read(content_length))
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object")
        return payload

    @staticmethod
    def _respond_json(
        start_response: Callable[..., Any], status: str, payload: Any
    ) -> list[bytes]:
        body = json.dumps(payload).encode("utf-8")
        start_response(
            status,
            [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
            ],
        )
        return [body]

    def _serve_static(
        self, method: str, path: str, start_response: Callable[..., Any]
    ) -> list[bytes]:
        if method != "GET":
            start_response("405 Method Not Allowed", [("Allow", "GET")])
            return [b""]
        relative_path = "index.html" if path == "/" else path.lstrip("/")
        file_path = (self.static_dir / relative_path).resolve()
        if self.static_dir not in file_path.parents and file_path != self.static_dir:
            start_response("404 Not Found", [])
            return [b"Not found"]
        try:
            body = file_path.read_bytes()
        except OSError:
            start_response("404 Not Found", [])
            return [b"Not found"]
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type == "application/javascript":
            content_type += "; charset=utf-8"
        start_response(
            "200 OK",
            [("Content-Type", content_type), ("Content-Length", str(len(body)))],
        )
        return [body]


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


def create_app(
    service: IncidentService, static_dir: str | Path | None = None
) -> IncidentAPI:
    if static_dir is None:
        static_dir = Path(__file__).resolve().parents[2] / "uis/backoffice/incidents"
    return IncidentAPI(service, Path(static_dir))