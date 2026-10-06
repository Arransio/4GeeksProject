"""Focused tests for incident persistence, transitions, and audit history."""

import unittest

from services.incident_manager.service import (
    IncidentCatalogs,
    IncidentService,
    InvalidIncident,
)


def test_catalogs() -> IncidentCatalogs:
    return IncidentCatalogs(
        incident_types=("fixture-type",),
        severities=("fixture-high", "fixture-low"),
        channels=("fixture-channel",),
        areas=("Technology", "Compliance and Data Governance"),
        statuses=("fixture-open", "fixture-active", "fixture-closed"),
        closed_statuses=("fixture-closed",),
        initial_status="fixture-open",
        transitions={"fixture-open": ("fixture-active",), "fixture-active": ("fixture-closed",)},
    )


class IncidentServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = IncidentService(":memory:", test_catalogs())
        self.incident = self.service.create_incident(
            title="Test incident",
            description="Fixture description",
            incident_type="fixture-type",
            severity="fixture-high",
            channel="fixture-channel",
            responsible_area="Technology",
            actor="operator@example.test",
        )

    def tearDown(self) -> None:
        self.service.close()

    def test_create_incident_records_initial_event(self) -> None:
        history = self.service.get_history(self.incident["incident_id"])

        self.assertEqual(self.incident["status"], "fixture-open")
        self.assertEqual(history[0]["event_type"], "created")
        self.assertEqual(history[0]["actor"], "operator@example.test")
        self.assertTrue(history[0]["occurred_at"])

    def test_assignment_and_status_changes_are_audited(self) -> None:
        incident_id = self.incident["incident_id"]
        self.service.assign_incident(
            incident_id,
            responsible_area="Compliance and Data Governance",
            actor="ops-lead@example.test",
        )
        self.service.transition_incident(
            incident_id, status="fixture-active", actor="compliance@example.test"
        )

        history = self.service.get_history(incident_id)
        self.assertEqual(history[-2]["event_type"], "responsibility_changed")
        self.assertEqual(history[-2]["actor"], "ops-lead@example.test")
        self.assertEqual(history[-2]["old_value"], "Technology")
        self.assertEqual(history[-2]["new_value"], "Compliance and Data Governance")
        self.assertEqual(history[-1]["event_type"], "status_changed")
        self.assertEqual(history[-1]["actor"], "compliance@example.test")
        self.assertTrue(history[-1]["occurred_at"])

    def test_invalid_catalog_value_is_rejected(self) -> None:
        with self.assertRaisesRegex(InvalidIncident, "Unsupported severity"):
            self.service.update_incident(
                self.incident["incident_id"], severity="unapproved-severity", actor="operator"
            )

    def test_invalid_transition_is_rejected_without_event(self) -> None:
        with self.assertRaisesRegex(InvalidIncident, "Transition not allowed"):
            self.service.transition_incident(
                self.incident["incident_id"], status="fixture-closed", actor="operator"
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
            len(self.service.list_incidents(status="fixture-open", severity="fixture-high")),
            1,
        )
        self.assertEqual(
            self.service.list_incidents(responsible_area="Compliance and Data Governance"),
            [],
        )
        self.assertEqual(
            self.service.open_incidents_by_severity(),
            {"fixture-high": 1, "fixture-low": 0},
        )

    def test_closed_incident_is_excluded_from_open_summary(self) -> None:
        incident_id = self.incident["incident_id"]
        self.service.transition_incident(
            incident_id, status="fixture-active", actor="operator"
        )
        self.service.transition_incident(
            incident_id, status="fixture-closed", actor="operator"
        )

        self.assertEqual(
            self.service.open_incidents_by_severity(),
            {"fixture-high": 0, "fixture-low": 0},
        )


if __name__ == "__main__":
    unittest.main()