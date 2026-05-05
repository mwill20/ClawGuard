import json
import tempfile
import unittest
from pathlib import Path

from scripts import export_telemetry
from scripts import telemetry_redaction


class TelemetryRedactionTests(unittest.TestCase):
    def test_redacts_email_phone_remote_and_deployment_identifiers(self):
        text = (
            "Contact user@example.com or (206) 555-1212. "
            "Run ssh root@31.97.139.139 and inspect openclaw-utxu-openclaw-1 "
            "under /docker/openclaw-utxu/data."
        )

        redacted = telemetry_redaction.redact_text(text)

        self.assertNotIn("user@example.com", redacted)
        self.assertNotIn("(206) 555-1212", redacted)
        self.assertNotIn("root@31.97.139.139", redacted)
        self.assertNotIn("openclaw-utxu", redacted)
        self.assertIn("<REDACTED_EMAIL>", redacted)
        self.assertIn("<REDACTED_PHONE>", redacted)
        self.assertIn("<REDACTED_REMOTE>", redacted)
        self.assertIn("<REDACTED_DEPLOYMENT>", redacted)

    def test_redacts_configured_profile_strings(self):
        config = telemetry_redaction.build_config(private_strings=["Private Employer"])

        redacted = telemetry_redaction.redact_text(
            "Candidate worked at Private Employer on SOC automation.",
            config,
        )

        self.assertNotIn("Private Employer", redacted)
        self.assertIn("<REDACTED_PROFILE_STRING>", redacted)

    def test_redacts_configured_extra_patterns(self):
        config = telemetry_redaction.build_config(extra_patterns=[r"ticket-\d+"])

        redacted = telemetry_redaction.redact_text("Reviewer note ticket-1234", config)

        self.assertEqual(redacted, "Reviewer note <REDACTED_CUSTOM>")

    def test_redacts_nested_json_values_without_changing_types(self):
        payload = {
            "agent_session_id": "digest-20260505T163003-5ba489e3",
            "finding_count": 1,
            "findings": [
                {
                    "message": "Send resume to user@example.com",
                    "evidence": {"phones": ["206-555-1212"]},
                }
            ],
        }

        redacted = telemetry_redaction.redact_value(payload)

        self.assertEqual(redacted["finding_count"], 1)
        self.assertEqual(redacted["findings"][0]["message"], "Send resume to <REDACTED_EMAIL>")
        self.assertEqual(redacted["findings"][0]["evidence"]["phones"], ["<REDACTED_PHONE>"])

    def test_redact_json_text_returns_valid_json(self):
        raw = json.dumps({"contact": "user@example.com"})

        redacted = json.loads(telemetry_redaction.redact_json_text(raw))

        self.assertEqual(redacted, {"contact": "<REDACTED_EMAIL>"})

    def test_export_writes_redacted_session_and_month_index(self):
        with tempfile.TemporaryDirectory() as temp:
            input_dir = Path(temp) / "input"
            output_dir = Path(temp) / "output"
            input_dir.mkdir()
            session = "digest-20260505T163003-5ba489e3"
            stem = f"telemetry_2026-05-05_{session}"
            payload = {
                "schema_version": "1.1",
                "generated_at": "2026-05-05T16:30:03",
                "digest_path": "/docker/openclaw-utxu/data/user@example.com/digest.json",
                "agent_session_id": session,
                "finding_count": 0,
                "rule_counts": {},
                "severity_counts": {},
                "finding_source_platform_counts": {},
                "digest_top_match_source_counts": {},
                "digest_summary": {
                    "total_found": 0,
                    "new_jobs": 0,
                    "auto_prepared": 0,
                    "credits_used_today": 0,
                },
                "findings": [],
            }
            (input_dir / f"{stem}.json").write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
            (input_dir / f"{stem}.md").write_text(
                "Contact user@example.com or 206-555-1212.",
                encoding="utf-8",
            )

            candidates = export_telemetry._selected_candidates(
                export_telemetry.load_candidates(input_dir),
                [session],
            )
            exported = export_telemetry.export_candidates(
                candidates,
                output_dir,
                telemetry_redaction.DEFAULT_CONFIG,
            )

            session_dir = output_dir / "2026-05" / session
            self.assertEqual(exported, [session_dir])
            redacted_json = json.loads((session_dir / "telemetry.json").read_text(encoding="utf-8"))
            redacted_md = (session_dir / "telemetry.md").read_text(encoding="utf-8")
            index_md = (output_dir / "2026-05" / "index.md").read_text(encoding="utf-8")

            self.assertNotIn("user@example.com", json.dumps(redacted_json))
            self.assertNotIn("user@example.com", redacted_md)
            self.assertNotIn("206-555-1212", redacted_md)
            self.assertIn(session, index_md)

    def test_export_dry_run_does_not_write_files(self):
        with tempfile.TemporaryDirectory() as temp:
            input_dir = Path(temp) / "input"
            output_dir = Path(temp) / "output"
            input_dir.mkdir()
            session = "digest-20260505T163003-5ba489e3"
            payload = {
                "schema_version": "1.1",
                "generated_at": "2026-05-05T16:30:03",
                "digest_path": "/data/clawguard/digests/digest_2026-05-05.json",
                "agent_session_id": session,
                "finding_count": 0,
                "rule_counts": {},
                "severity_counts": {},
                "finding_source_platform_counts": {},
                "digest_top_match_source_counts": {},
                "digest_summary": {
                    "total_found": 0,
                    "new_jobs": 0,
                    "auto_prepared": 0,
                    "credits_used_today": 0,
                },
                "findings": [],
            }
            (input_dir / "telemetry_latest.json").write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

            candidates = export_telemetry._selected_candidates(
                export_telemetry.load_candidates(input_dir),
                [session],
            )
            exported = export_telemetry.export_candidates(
                candidates,
                output_dir,
                telemetry_redaction.DEFAULT_CONFIG,
                dry_run=True,
            )

            self.assertEqual(exported, [output_dir / "2026-05" / session])
            self.assertFalse(output_dir.exists())


if __name__ == "__main__":
    unittest.main()
