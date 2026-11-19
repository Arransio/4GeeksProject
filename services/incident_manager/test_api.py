"""HTTP integration tests for the FastAPI incident manager."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from services.incident_manager.api import create_app, load_catalogs
from services.incident_manager.service import IncidentService


class IncidentAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        catalogs = load_catalogs(Path(__file__).with_name("catalogs.json"))
        self.service = IncidentService(":memory:", catalogs)
        static_dir = Path(self.temporary_directory.name)
        (static_dir / "index.html").write_text("<main>Incident desk</main>", encoding="utf-8")
        self.app = create_app(self.service, static_dir)
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.service.close()
        self.temporary_directory.cleanup()

    def create_incident(self):
        return self.client.post(
            "/api/incidents",
            json={
                "title": "Fixture incident",
                "description": "No patient information",
                "incident_type": "Sistemas y accesos",
                "severity": "Crítica",
                "channel": "Llamada de clínica",
                "responsible_area": "Tecnología",
            },
            headers={"X-Actor": "operator@example.test"},
        )

    def test_create_filter_assignment_transition_history_and_summary(self) -> None:
        created = self.create_incident()
        self.assertEqual(created.status_code, 201)
        incident = created.json()

        listing = self.client.get(
            "/api/incidents", params={"severity": "Crítica", "status": "Abierta"}
        )
        self.assertEqual(len(listing.json()), 1)

        assigned = self.client.patch(
            f"/api/incidents/{incident['incident_id']}",
            json={"responsible_area": "Operaciones Clínicas"},
            headers={"X-Actor": "operations@example.test"},
        )
        self.assertEqual(assigned.status_code, 200)
        self.assertEqual(assigned.json()["responsible_area"], "Operaciones Clínicas")

        transitioned = self.client.patch(
            f"/api/incidents/{incident['incident_id']}",
            json={"status": "En revisión"},
            headers={"X-Actor": "technology@example.test"},
        )
        self.assertEqual(transitioned.status_code, 200)

        history = self.client.get(f"/api/incidents/{incident['incident_id']}/history")
        events = history.json()
        self.assertEqual(events[-2]["event_type"], "responsibility_changed")
        self.assertEqual(events[-2]["actor"], "operations@example.test")
        self.assertEqual(events[-1]["event_type"], "status_changed")
        self.assertEqual(events[-1]["actor"], "technology@example.test")

        summary = self.client.get("/api/summary/open-by-severity")
        self.assertEqual(
            summary.json(), {"Crítica": 1, "Alta": 0, "Media": 0, "Baja": 0}
        )

    def test_write_requires_actor_and_catalog_values(self) -> None:
        missing_actor = self.client.post(
            "/api/incidents",
            json={
                "title": "Fixture incident",
                "description": "Fixture description",
                "incident_type": "Sistemas y accesos",
                "severity": "Crítica",
                "channel": "Llamada de clínica",
                "responsible_area": "Tecnología",
            },
        )
        self.assertEqual(missing_actor.status_code, 422)

        invalid_catalog_value = self.client.post(
            "/api/incidents",
            json={
                "title": "Fixture incident",
                "description": "Fixture description",
                "incident_type": "Tipo desconocido",
                "severity": "Crítica",
                "channel": "Llamada de clínica",
                "responsible_area": "Tecnología",
            },
            headers={"X-Actor": "operator@example.test"},
        )
        self.assertEqual(invalid_catalog_value.status_code, 400)

    def test_catalog_route_and_static_backoffice(self) -> None:
        catalogs = self.client.get("/api/catalogs")
        payload = catalogs.json()
        self.assertEqual(payload["closed_statuses"], ["Cerrada"])
        self.assertEqual(payload["initial_status"], "Abierta")
        self.assertIn("Facturación", payload["incident_types"])

        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.text, "<main>Incident desk</main>")

        schema = self.client.get("/openapi.json").json()
        self.assertIn("/api/incidents", schema["paths"])
        self.assertIn("/api/incidents/{incident_id}/history", schema["paths"])


if __name__ == "__main__":
    unittest.main()