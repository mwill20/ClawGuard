import json
import tempfile
import unittest
from pathlib import Path

from scripts import select_review_sessions


def write_session(directory: Path, name: str, **overrides):
    payload = {
        "agent_session_id": f"digest-{name}",
        "schema_version": "1.1",
        "generated_at": "2026-05-05T16:30:00",
        "finding_count": 0,
        "findings": [],
        "rule_counts": {},
    }
    payload.update(overrides)
    path = directory / f"telemetry_{name}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class SelectReviewSessionsTests(unittest.TestCase):
    def test_selects_sessions_by_rule_id(self):
        with tempfile.TemporaryDirectory() as temp:
            telemetry_dir = Path(temp)
            write_session(
                telemetry_dir,
                "asi01",
                finding_count=1,
                findings=[{"rule_id": "ASI01_EXTERNAL_GOAL_REDIRECT"}],
            )
            write_session(telemetry_dir, "clean")

            sessions = select_review_sessions.load_sessions(telemetry_dir)
            selected = select_review_sessions.select_sessions(
                sessions, rule="ASI01_EXTERNAL_GOAL_REDIRECT"
            )

            self.assertEqual([session.session_id for session in selected], ["digest-asi01"])

    def test_selects_sessions_by_finding_count_minimum(self):
        with tempfile.TemporaryDirectory() as temp:
            telemetry_dir = Path(temp)
            write_session(telemetry_dir, "clean")
            write_session(telemetry_dir, "one", finding_count=1)
            write_session(telemetry_dir, "two", finding_count=2)

            selected = select_review_sessions.select_sessions(
                select_review_sessions.load_sessions(telemetry_dir),
                finding_count_min=1,
            )

            self.assertEqual(
                [session.session_id for session in selected],
                ["digest-one", "digest-two"],
            )

    def test_selects_sessions_by_date_range(self):
        with tempfile.TemporaryDirectory() as temp:
            telemetry_dir = Path(temp)
            write_session(telemetry_dir, "old", generated_at="2026-05-01T16:30:00")
            write_session(telemetry_dir, "new", generated_at="2026-05-05T16:30:00")

            selected = select_review_sessions.select_sessions(
                select_review_sessions.load_sessions(telemetry_dir),
                since=select_review_sessions._parse_date("2026-05-03"),
            )

            self.assertEqual([session.session_id for session in selected], ["digest-new"])

    def test_selects_clean_baseline_sessions(self):
        with tempfile.TemporaryDirectory() as temp:
            telemetry_dir = Path(temp)
            write_session(telemetry_dir, "clean")
            write_session(telemetry_dir, "finding", finding_count=1)

            selected = select_review_sessions.select_sessions(
                select_review_sessions.load_sessions(telemetry_dir),
                baseline=True,
            )

            self.assertEqual([session.session_id for session in selected], ["digest-clean"])


if __name__ == "__main__":
    unittest.main()
