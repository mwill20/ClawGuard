# ASI03 Identity and Privilege Abuse

Status: Runtime detector v1 implemented locally; observe-only.

ASI03 detects identity and credential misuse from `runtime-events/0.1`
artifacts. It does not scan job-description text.

## Rules

| Rule | Meaning |
|---|---|
| `ASI03_UNKNOWN_CREDENTIAL_LABEL` | A runtime event used a credential label outside the approved provider inventory. |
| `ASI03_CREDENTIAL_EGRESS_MISMATCH` | A session combined an unapproved credential label with non-approved network egress. |

## Safety

Findings store labels and event IDs only. They must not persist raw secrets,
tokens, private paths, host identifiers, or credential material.
