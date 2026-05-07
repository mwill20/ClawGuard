import json
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import export_telemetry
from scripts import export_runtime_events
from scripts import telemetry_redaction
from scripts import validate_runtime_events


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_REDACTOR_PATH = (
    ROOT / "target-agent" / "skills" / "job-search-custom" / "clawguard_redact_runtime_events.py"
)
redactor_spec = importlib.util.spec_from_file_location("clawguard_redact_runtime_events", RUNTIME_REDACTOR_PATH)
runtime_event_redactor = importlib.util.module_from_spec(redactor_spec)
sys.modules[redactor_spec.name] = runtime_event_redactor
redactor_spec.loader.exec_module(runtime_event_redactor)


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

    def test_export_materializes_legacy_schema_version(self):
        payload = {
            "generated_at": "2026-05-05T16:30:03",
            "digest_path": "/data/clawguard/digests/digest_2026-05-05.json",
            "agent_session_id": "digest-20260505T163003-5ba489e3",
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

        redacted = export_telemetry._redacted_payload(
            payload,
            telemetry_redaction.DEFAULT_CONFIG,
        )

        self.assertEqual(redacted["schema_version"], "1.0")

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

    def test_runtime_event_host_redactor_adds_status_and_removes_sensitive_values(self):
        payload = {
            "schema_version": "runtime-events/0.1",
            "generated_at": "2026-05-07T04:10:20Z",
            "agent_session_id": "digest-20260507T041020-50c7d030",
            "events": [
                {
                    "event_id": "evt-digest-20260507T041020-50c7d030-identity-001",
                    "event_time": "2026-05-07T04:10:20Z",
                    "agent_session_id": "digest-20260507T041020-50c7d030",
                    "event_type": "identity_context",
                    "actor": {"type": "agent", "id": "openclaw-job-search"},
                    "source": {
                        "component": "job_search_secure.py",
                        "code_path": "target-agent/skills/job-search-custom/job_search_secure.py",
                    },
                    "operation": "set_identity_context",
                    "operation_category": "identity-context",
                    "target": {
                        "kind": "service_identity",
                        "label": "openclaw-job-search-profile",
                        "redaction_status": "label_only",
                    },
                    "policy": {"decision": "observe", "reason": "baseline"},
                    "correlation": {
                        "agent_session_id": "digest-20260507T041020-50c7d030",
                        "related_rule_ids": [],
                    },
                    "evidence": {
                        "contact": "user@example.com / 206-555-1212",
                        "remote": "root@31.97.139.139",
                        "deployment": "openclaw-utxu-openclaw-1",
                        "host_path": "/docker/openclaw-utxu/data/clawguard/runtime_events/runtime_events_latest.json",
                        "container_path": "/data/clawguard/runtime_events/runtime_events_latest.json",
                    },
                }
            ],
        }

        redacted = runtime_event_redactor.redact_runtime_events_payload(payload)
        serialized = json.dumps(redacted)
        result = validate_runtime_events.validate_runtime_events(redacted)

        self.assertEqual(result["status"], "valid")
        self.assertEqual(redacted["redaction"]["status"], "host_redacted")
        self.assertNotIn("user@example.com", serialized)
        self.assertNotIn("206-555-1212", serialized)
        self.assertNotIn("root@31.97.139.139", serialized)
        self.assertNotIn("openclaw-utxu", serialized)
        self.assertNotIn("/data/clawguard", serialized)
        self.assertIn("openclaw-job-search-profile", serialized)

    def test_runtime_event_host_redactor_relabels_raw_path_stored_flag(self):
        payload = {
            "schema_version": "runtime-events/0.1",
            "generated_at": "2026-05-07T04:10:20Z",
            "agent_session_id": "digest-20260507T041020-50c7d030",
            "events": [
                {
                    "event_id": "evt-digest-20260507T041020-50c7d030-file-001",
                    "event_time": "2026-05-07T04:10:20Z",
                    "agent_session_id": "digest-20260507T041020-50c7d030",
                    "event_type": "file_write",
                    "actor": {"type": "agent", "id": "openclaw-job-search"},
                    "source": {"component": "test", "code_path": "test"},
                    "operation": "runtime_event_write",
                    "operation_category": "file-write",
                    "target": {
                        "kind": "path_label",
                        "label": "runtime-events",
                        "redaction_status": "label_only",
                    },
                    "policy": {"decision": "allow", "reason": "test"},
                    "correlation": {
                        "agent_session_id": "digest-20260507T041020-50c7d030",
                        "related_rule_ids": [],
                    },
                    "evidence": {"raw_path_stored": False},
                }
            ],
        }

        redacted = runtime_event_redactor.redact_runtime_events_payload(payload)
        evidence = redacted["events"][0]["evidence"]
        serialized = json.dumps(redacted)

        self.assertNotIn("raw_path_stored", evidence)
        self.assertTrue(evidence["path_label_only"])
        self.assertNotIn("raw_path", serialized)

    def test_runtime_event_host_redactor_relabels_sensitive_keys(self):
        payload = {
            "schema_version": "runtime-events/0.1",
            "generated_at": "2026-05-07T04:10:20Z",
            "agent_session_id": "digest-20260507T041020-50c7d030",
            "events": [
                {
                    "event_id": "evt-digest-20260507T041020-50c7d030-credential-001",
                    "event_time": "2026-05-07T04:10:20Z",
                    "agent_session_id": "digest-20260507T041020-50c7d030",
                    "event_type": "credential_use",
                    "actor": {"type": "agent", "id": "openclaw-job-search"},
                    "source": {"component": "test", "code_path": "test"},
                    "operation": "read_provider_credential_label",
                    "operation_category": "credential-use",
                    "target": {
                        "kind": "credential_label",
                        "label": "usajobs-search-provider-credential",
                        "redaction_status": "redacted",
                    },
                    "policy": {"decision": "allow", "reason": "test"},
                    "correlation": {
                        "agent_session_id": "digest-20260507T041020-50c7d030",
                        "related_rule_ids": [],
                    },
                    "evidence": {
                        "api_key": "should-not-survive",
                        "raw_command": "curl https://example.com?token=should-not-survive",
                    },
                }
            ],
        }

        redacted = runtime_event_redactor.redact_runtime_events_payload(payload)
        evidence = redacted["events"][0]["evidence"]
        result = validate_runtime_events.validate_runtime_events(redacted)

        self.assertEqual(result["status"], "valid")
        self.assertNotIn("api_key", evidence)
        self.assertNotIn("raw_command", evidence)
        self.assertEqual(evidence["credential_label"], "<REDACTED_SENSITIVE_VALUE>")
        self.assertEqual(evidence["command_label"], "<REDACTED_SENSITIVE_VALUE>")

    def test_runtime_event_export_requires_host_redaction_and_writes_index(self):
        payload = {
            "schema_version": "runtime-events/0.1",
            "generated_at": "2026-05-07T04:10:20Z",
            "agent_session_id": "digest-20260507T041020-50c7d030",
            "events": [
                {
                    "event_id": "evt-digest-20260507T041020-50c7d030-identity-001",
                    "event_time": "2026-05-07T04:10:20Z",
                    "agent_session_id": "digest-20260507T041020-50c7d030",
                    "event_type": "identity_context",
                    "actor": {"type": "agent", "id": "openclaw-job-search"},
                    "source": {"component": "test", "code_path": "test"},
                    "operation": "set_identity_context",
                    "operation_category": "identity-context",
                    "target": {
                        "kind": "service_identity",
                        "label": "openclaw-job-search-profile",
                        "redaction_status": "label_only",
                    },
                    "policy": {"decision": "observe", "reason": "test"},
                    "correlation": {
                        "agent_session_id": "digest-20260507T041020-50c7d030",
                        "related_rule_ids": [],
                    },
                    "evidence": {},
                }
            ],
        }
        redacted = runtime_event_redactor.redact_runtime_events_payload(payload)

        with tempfile.TemporaryDirectory() as temp:
            input_dir = Path(temp) / "input"
            output_dir = Path(temp) / "output"
            input_dir.mkdir()
            (input_dir / "runtime_events_latest.redacted.json").write_text(
                json.dumps(redacted),
                encoding="utf-8",
            )

            candidates = export_runtime_events._selected_candidates(
                export_runtime_events.load_candidates(input_dir),
                ["digest-20260507T041020-50c7d030"],
            )
            exported = export_runtime_events.export_candidates(candidates, output_dir)

            session_dir = output_dir / "2026-05" / "digest-20260507T041020-50c7d030"
            self.assertEqual(exported, [session_dir])
            exported_json = json.loads((session_dir / "runtime_events.json").read_text(encoding="utf-8"))
            exported_md = (session_dir / "runtime_events.md").read_text(encoding="utf-8")
            index_md = (output_dir / "2026-05" / "index.md").read_text(encoding="utf-8")

            self.assertEqual(exported_json["redaction"]["status"], "host_redacted")
            self.assertIn("identity_context", exported_md)
            self.assertIn("digest-20260507T041020-50c7d030", index_md)

    def test_runtime_event_export_rejects_missing_redaction_status(self):
        payload = {
            "schema_version": "runtime-events/0.1",
            "generated_at": "2026-05-07T04:10:20Z",
            "agent_session_id": "digest-20260507T041020-50c7d030",
            "events": [],
        }

        with tempfile.TemporaryDirectory() as temp:
            input_dir = Path(temp) / "input"
            input_dir.mkdir()
            (input_dir / "runtime_events_latest.redacted.json").write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

            with self.assertRaises(export_runtime_events.RuntimeEventExportError):
                export_runtime_events.load_candidates(input_dir)


if __name__ == "__main__":
    unittest.main()
