import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "target-agent" / "skills" / "job-search-custom" / "runtime_events.py"
VALIDATOR_PATH = ROOT / "scripts" / "validate_runtime_events.py"
SESSION_ID = "digest-20260506T163000-1234abcd"

writer_spec = importlib.util.spec_from_file_location("runtime_events", WRITER_PATH)
runtime_events = importlib.util.module_from_spec(writer_spec)
sys.modules[writer_spec.name] = runtime_events
writer_spec.loader.exec_module(runtime_events)

validator_spec = importlib.util.spec_from_file_location("validate_runtime_events", VALIDATOR_PATH)
validate_runtime_events = importlib.util.module_from_spec(validator_spec)
validator_spec.loader.exec_module(validate_runtime_events)


class RuntimeEventsWriterTests(unittest.TestCase):
    def setUp(self):
        self.old_enabled = os.environ.get("CLAWGUARD_RUNTIME_EVENTS_ENABLED")
        self.old_dir = os.environ.get("CLAWGUARD_RUNTIME_EVENTS_DIR")
        runtime_events.reset_for_tests()

    def tearDown(self):
        if self.old_enabled is None:
            os.environ.pop("CLAWGUARD_RUNTIME_EVENTS_ENABLED", None)
        else:
            os.environ["CLAWGUARD_RUNTIME_EVENTS_ENABLED"] = self.old_enabled
        if self.old_dir is None:
            os.environ.pop("CLAWGUARD_RUNTIME_EVENTS_DIR", None)
        else:
            os.environ["CLAWGUARD_RUNTIME_EVENTS_DIR"] = self.old_dir
        runtime_events.reset_for_tests()

    def test_disabled_writer_is_silent(self):
        os.environ.pop("CLAWGUARD_RUNTIME_EVENTS_ENABLED", None)
        with tempfile.TemporaryDirectory() as temp:
            session = runtime_events.start_runtime_event_session(
                SESSION_ID,
                output_dir=Path(temp),
                generated_at="2026-05-06T16:30:00Z",
            )
            recorded = runtime_events.record_runtime_event(
                runtime_events.build_runtime_event(
                    event_type="identity_context",
                    operation="set_identity_context",
                    operation_category="identity-context",
                    target_kind="service_identity",
                    target_label="openclaw-maintenance-profile",
                    evidence={"credential_material_present": False},
                )
            )

            self.assertIsNone(session)
            self.assertFalse(recorded)
            self.assertIsNone(runtime_events.flush_runtime_events())
            self.assertEqual([], list(Path(temp).iterdir()))

    def test_enabled_writer_round_trips_through_runtime_validator(self):
        os.environ["CLAWGUARD_RUNTIME_EVENTS_ENABLED"] = "1"
        with tempfile.TemporaryDirectory() as temp:
            runtime_events.start_runtime_event_session(
                SESSION_ID,
                output_dir=Path(temp),
                generated_at="2026-05-06T16:30:00Z",
            )

            runtime_events.record_runtime_event(
                runtime_events.build_runtime_event(
                    event_type="identity_context",
                    operation="set_identity_context",
                    operation_category="identity-context",
                    target_kind="service_identity",
                    target_label="openclaw-maintenance-profile",
                    policy_decision="observe",
                    policy_reason="baseline identity context",
                    evidence={
                        "profile_path_label": "CLAWGUARD_PROFILE_PATH",
                        "credential_material_present": False,
                    },
                )
            )
            runtime_events.record_runtime_event(
                runtime_events.build_runtime_event(
                    event_type="credential_use",
                    operation="read_provider_credential_label",
                    operation_category="credential-use",
                    target_kind="credential_label",
                    target_label="brave-search-provider-credential",
                    target_redaction_status="redacted",
                    policy_decision="allow",
                    policy_reason="approved search provider credential",
                    evidence={
                        "credential_purpose": "provider_api_auth",
                        "raw_value_stored": False,
                    },
                )
            )
            runtime_events.record_runtime_event(
                runtime_events.build_runtime_event(
                    event_type="network_egress",
                    operation="search_provider_request",
                    operation_category="http-egress",
                    target_kind="domain",
                    target_label="api.search.brave.com",
                    policy_decision="allow",
                    policy_reason="safe egress allowlist",
                    evidence={
                        "destination_category": "search-provider",
                        "request_body_stored": False,
                    },
                )
            )
            runtime_events.record_runtime_event(
                runtime_events.build_runtime_event(
                    event_type="process_exec",
                    actor_type="automation",
                    actor_id="local-preflight",
                    source_component="scripts/preflight.ps1",
                    source_code_path="scripts/preflight.ps1",
                    operation="run_unit_tests",
                    operation_category="process-exec",
                    target_kind="command_label",
                    target_label="python unittest discover",
                    policy_decision="allow",
                    policy_reason="approved validation command",
                    evidence={
                        "cwd_label": "repo-root",
                        "exit_code": 0,
                        "arguments_stored": "label_only",
                    },
                )
            )

            archive_path = runtime_events.flush_runtime_events()
            latest_path = Path(temp) / "runtime_events_latest.json"
            result = validate_runtime_events.load_and_validate(
                archive_path,
                require=["asi03", "asi05"],
            )
            data = json.loads(archive_path.read_text(encoding="utf-8"))

            self.assertEqual(result["status"], "valid")
            self.assertEqual(result["schema_version"], "runtime-events/0.1")
            self.assertEqual(result["agent_session_id"], SESSION_ID)
            self.assertEqual(result["event_type_counts"]["file_write"], 1)
            self.assertTrue(latest_path.exists())
            self.assertEqual(data["events"][-1]["operation"], "runtime_event_write")
            self.assertEqual(
                data["events"][-1]["evidence"]["self_emission_guard"],
                "direct_append_no_record_call",
            )

    def test_sensitive_field_names_are_rejected_before_persistence(self):
        os.environ["CLAWGUARD_RUNTIME_EVENTS_ENABLED"] = "1"
        with tempfile.TemporaryDirectory() as temp:
            runtime_events.start_runtime_event_session(SESSION_ID, output_dir=Path(temp))

            with self.assertRaises(runtime_events.RuntimeEventWriterError):
                runtime_events.record_runtime_event(
                    runtime_events.build_runtime_event(
                        event_type="credential_use",
                        operation="read_provider_credential_label",
                        operation_category="credential-use",
                        target_kind="credential_label",
                        target_label="brave-search-provider-credential",
                        evidence={"token_value": "redacted-token-placeholder"},
                    )
                )

            self.assertEqual([], list(Path(temp).iterdir()))

    def test_raw_private_paths_are_rejected_before_persistence(self):
        os.environ["CLAWGUARD_RUNTIME_EVENTS_ENABLED"] = "1"
        with tempfile.TemporaryDirectory() as temp:
            runtime_events.start_runtime_event_session(SESSION_ID, output_dir=Path(temp))

            with self.assertRaises(runtime_events.RuntimeEventWriterError):
                runtime_events.record_runtime_event(
                    runtime_events.build_runtime_event(
                        event_type="file_write",
                        operation="write_digest",
                        operation_category="file-write",
                        target_kind="path_label",
                        target_label="digest-output",
                        evidence={"path_label": "digest-output", "raw_path": r"C:\Users\20mdw\resume.txt"},
                    )
                )

            self.assertEqual([], list(Path(temp).iterdir()))

    def test_invalid_agent_session_id_is_rejected(self):
        os.environ["CLAWGUARD_RUNTIME_EVENTS_ENABLED"] = "1"
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(runtime_events.RuntimeEventWriterError):
                runtime_events.start_runtime_event_session(
                    "missing-session-id",
                    output_dir=Path(temp),
                )

            self.assertEqual([], list(Path(temp).iterdir()))

    def test_flush_is_idempotent_and_does_not_duplicate_self_write_event(self):
        os.environ["CLAWGUARD_RUNTIME_EVENTS_ENABLED"] = "1"
        with tempfile.TemporaryDirectory() as temp:
            runtime_events.start_runtime_event_session(
                SESSION_ID,
                output_dir=Path(temp),
                generated_at="2026-05-06T16:30:00Z",
            )

            first_path = runtime_events.flush_runtime_events()
            second_path = runtime_events.flush_runtime_events()
            data = json.loads(first_path.read_text(encoding="utf-8"))
            self_write_events = [
                event for event in data["events"]
                if event["operation"] == "runtime_event_write"
            ]

            self.assertEqual(first_path, second_path)
            self.assertEqual(len(self_write_events), 1)


if __name__ == "__main__":
    unittest.main()
