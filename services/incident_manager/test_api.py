"""WSGI integration tests for the incident manager API and backoffice shell."""

from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from services.incident_manager.api import create_app
from services.incident_manager.service import IncidentCatalogs, IncidentService


class IncidentAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.service = IncidentService(
            ":memory:",
            IncidentCatalogs(
                incident_types=("fixture-type",),
                severities=("fixture-high", "fixture-low"),
                channels=("fixture-channel",),
                areas=("Tecnología", "Operaciones Clínicas"),
                statuses=("fixture-open", "fixture-active", "fixture-closed"),
                closed_statuses=("fixture-closed",),
                initial_status="fixture-open",
                transitions={
                    "fixture-open": ("fixture-active",),
                    "fixture-active": ("fixture-closed",),
                },
            ),
        )
        static_dir = Path(self.temporary_directory.name)
        (static_dir / "index.html").write_text("<main>Incident desk</main>", encoding="utf-8")
        self.app = create_app(self.service, static_dir)

    def tearDown(self) -> None:
        self.service.close()
        self.temporary_directory.cleanup()

    def call(self, method: str, path: str, payload: dict | None = None, actor: str = ""):
        body = json.dumps(payload).encode("utf-8") if payload is not None else b""
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": "",
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
        }
        if actor:
            environ["HTTP_X_ACTOR"] = actor
        response: dict[str, object] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            response["status"] = status
            response["headers"] = headers

        output = b"".join(self.app(environ, start_response))
        response["body"] = output
        return response

    def test_create_filter_history_and_summary_routes(self) -> None:
        created = self.call(
            "POST",
            "/api/incidents",
            {
                "title": "Fixture incident",
                "description": "No patient information",
                "incident_type": "fixture-type",
                "severity": "fixture-high",
                "channel": "fixture-channel",
                "responsible_area": "Tecnología",
            },
            actor="operator@example.test",
        )
        self.assertEqual(created["status"], "201 Created")
        incident = json.loads(created["body"])

        listing = self.call("GET", "/api/incidents?severity=fixture-high")
        self.assertEqual(len(json.loads(listing["body"])), 1)

        history = self.call("GET", f"/api/incidents/{incident['incident_id']}/history")
        self.assertEqual(json.loads(history["body"])[0]["actor"], "operator@example.test")

        assigned = self.call(
            "PATCH",
            f"/api/incidents/{incident['incident_id']}",
            {"responsible_area": "Operaciones Clínicas"},
            actor="operations@example.test",
        )
        self.assertEqual(assigned["status"], "200 OK")
        transitioned = self.call(
            "PATCH",
            f"/api/incidents/{incident['incident_id']}",
            {"status": "fixture-active"},
            actor="technology@example.test",
        )
        self.assertEqual(transitioned["status"], "200 OK")
        final_history = self.call("GET", f"/api/incidents/{incident['incident_id']}/history")
        self.assertEqual(json.loads(final_history["body"])[-1]["event_type"], "status_changed")

        summary = self.call("GET", "/api/summary/open-by-severity")
        self.assertEqual(json.loads(summary["body"]), {"fixture-high": 1, "fixture-low": 0})

    def test_write_requires_actor_and_catalog_values(self) -> None:
        missing_actor = self.call(
            "POST",
            "/api/incidents",
            {
                "title": "Fixture incident",
                "description": "Fixture description",
                "incident_type": "fixture-type",
                "severity": "fixture-high",
                "channel": "fixture-channel",
                "responsible_area": "Tecnología",
            },
        )
        self.assertEqual(missing_actor["status"], "400 Bad Request")

    def test_catalog_route_and_static_backoffice(self) -> None:
        catalogs = self.call("GET", "/api/catalogs")
        self.assertEqual(json.loads(catalogs["body"])["closed_statuses"], ["fixture-closed"])

        page = self.call("GET", "/")
        self.assertEqual(page["status"], "200 OK")
        self.assertEqual(page["body"], b"<main>Incident desk</main>")


if __name__ == "__main__":
    unittest.main()