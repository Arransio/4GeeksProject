"""Tests for the approved HealthCore incident catalogs and audit history."""

import unittest
from pathlib import Path

from services.incident_manager.api import load_catalogs
from services.incident_manager.service import IncidentService, InvalidIncident


def approved_catalogs():
    return load_catalogs(Path(__file__).with_name("catalogs.json"))


class IncidentServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = IncidentService(":memory:", approved_catalogs())
        self.incident = self.service.create_incident(
            title="Test incident",
            description="Fixture description",
            incident_type="Sistemas y accesos",
            severity="Crítica",
            channel="Llamada de clínica",
            responsible_area="Tecnología",
            actor="operator@example.test",
        )

    def tearDown(self) -> None:
        self.service.close()

    def test_create_incident_records_initial_event(self) -> None:
        history = self.service.get_history(self.incident["incident_id"])

        self.assertEqual(self.incident["status"], "Abierta")
        self.assertEqual(history[0]["event_type"], "created")
        self.assertEqual(history[0]["actor"], "operator@example.test")
        self.assertTrue(history[0]["occurred_at"])

    def test_assignment_and_status_changes_are_audited(self) -> None:
        incident_id = self.incident["incident_id"]
        self.service.assign_incident(
            incident_id,
            responsible_area="Cumplimiento y Gobierno del Dato",
            actor="ops-lead@example.test",
        )
        self.service.transition_incident(
            incident_id, status="En revisión", actor="compliance@example.test"
        )

        history = self.service.get_history(incident_id)
        self.assertEqual(history[-2]["event_type"], "responsibility_changed")
        self.assertEqual(history[-2]["actor"], "ops-lead@example.test")
        self.assertEqual(history[-2]["old_value"], "Tecnología")
        self.assertEqual(
            history[-2]["new_value"], "Cumplimiento y Gobierno del Dato"
        )
        self.assertEqual(history[-1]["event_type"], "status_changed")
        self.assertEqual(history[-1]["actor"], "compliance@example.test")
        self.assertTrue(history[-1]["occurred_at"])

    def test_invalid_catalog_value_is_rejected(self) -> None:
        with self.assertRaisesRegex(InvalidIncident, "Unsupported severity"):
            self.service.update_incident(
                self.incident["incident_id"], severity="No aprobada", actor="operator"
            )

    def test_invalid_transition_is_rejected_without_event(self) -> None:
        with self.assertRaisesRegex(InvalidIncident, "Transition not allowed"):
            self.service.transition_incident(
                self.incident["incident_id"], status="Cerrada", actor="operator"
            )

        self.assertEqual(len(self.service.get_history(self.incident["incident_id"])), 1)

    def test_update_changes_editable_fields_and_audits(self) -> None:
        self.service.update_incident(
            self.incident["incident_id"], title="Updated title", actor="operator"
        )

        updated = self.service.get_incident(self.incident["incident_id"])
        event = self.service.get_history(self.incident["incident_id"])[-1]
        self.assertEqual(updated["title"], "Updated title")
        self.assertEqual(event["field_name"], "title")
        self.assertEqual(event["old_value"], "Test incident")
        self.assertEqual(event["new_value"], "Updated title")

    def test_filters_and_open_summary(self) -> None:
        self.assertEqual(
            len(self.service.list_incidents(status="Abierta", severity="Crítica")),
            1,
        )
        self.assertEqual(
            self.service.list_incidents(
                responsible_area="Cumplimiento y Gobierno del Dato"
            ),
            [],
        )
        self.assertEqual(
            self.service.open_incidents_by_severity(),
            {"Crítica": 1, "Alta": 0, "Media": 0, "Baja": 0},
        )

    def test_approved_state_sequence_and_open_summary(self) -> None:
        incident_id = self.incident["incident_id"]
        for status in ("En revisión", "En curso", "Resuelta"):
            self.service.transition_incident(
                incident_id, status=status, actor="operator"
            )
        self.assertEqual(
            self.service.open_incidents_by_severity()["Crítica"], 1
        )
        self.service.transition_incident(
            incident_id, status="Cerrada", actor="operator"
        )

        self.assertEqual(
            self.service.open_incidents_by_severity(),
            {"Crítica": 0, "Alta": 0, "Media": 0, "Baja": 0},
        )


if __name__ == "__main__":
    unittest.main()