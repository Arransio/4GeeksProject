"""Verifica que SKILL.md cumple la estructura exigida a una skill.

Run: python3 -m unittest check_skill.py -v  (from skills/code-review/scripts/)
"""
import os
import re
import unittest

SKILL_PATH = os.path.join(os.path.dirname(__file__), "..", "SKILL.md")


def load_skill():
    with open(SKILL_PATH) as handle:
        return handle.read()


class SkillStructureTests(unittest.TestCase):
    def test_has_single_objective_section(self):
        text = load_skill()
        self.assertEqual(text.count("## Objetivo unico"), 1)

    def test_has_documented_inputs(self):
        text = load_skill()
        self.assertIn("## Inputs documentados", text)
        self.assertIn("| Input | Origen |", text)

    def test_has_explicit_acceptance_criteria(self):
        text = load_skill()
        criteria = re.findall(r"\*\*(CA-\d\d)\*\*", text)
        self.assertGreaterEqual(len(criteria), 4)
        self.assertEqual(criteria, sorted(set(criteria)))

    def test_each_criterion_is_verifiable(self):
        text = load_skill()
        criteria = re.findall(r"- \*\*(CA-\d\d)\*\*: (.+)", text)
        self.assertGreaterEqual(len(criteria), 4)
        for name, body in criteria:
            with self.subTest(criterion=name):
                self.assertGreater(len(body), 40, "criterion too short to verify")

    def test_read_only_commit(self):
        text = load_skill()
        self.assertIn("git commit", text)
        self.assertIn("solo lectura", text)


if __name__ == "__main__":
    unittest.main()