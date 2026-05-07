# ASI05 Unexpected Code Execution

Status: Runtime detector v1 implemented locally; observe-only.

ASI05 detects unexpected process/container labels from `runtime-events/0.1`
artifacts. It does not duplicate ASI02 content-side shell detection.

## Rules

| Rule | Meaning |
|---|---|
| `ASI05_UNAPPROVED_PROCESS_LABEL` | A `process_exec` event used a process label outside the approved inventory. |
| `ASI05_UNAPPROVED_CONTAINER_ACTION` | A `container_action` event used an unapproved container label or operation. |

## Safety

Findings store labels and event IDs only. They must not persist raw command
lines, arguments, private paths, host identifiers, container IDs, or secrets.
