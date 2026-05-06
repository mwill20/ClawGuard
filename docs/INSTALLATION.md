# Installation

## Local Requirements

| Requirement | Version / Notes |
|---|---|
| Python | Tested with Python 3.12.0; Python 3.11+ expected |
| Package manager | `pip` |
| OS | Windows PowerShell examples provided |
| GPU | Not required |
| External APIs | Not required for local tests |

## Quickstart

PowerShell:

```powershell
git clone https://github.com/mwill20/ClawGuard.git
Set-Location ClawGuard
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -B -m unittest discover -s tests
```

Expected output:

```text
........................
----------------------------------------------------------------------
Ran 54 tests in 0.0

OK
```

The exact runtime in seconds may vary.

## Environment Variables

Local detector tests do not require environment variables.

The deployed OpenClaw search pipeline uses variables documented in [.env.example](../.env.example), including:

- `BRAVE_SEARCH_API_KEY`
- `USAJOBS_AUTH_KEY`
- `USAJOBS_USER_AGENT`
- `CLAWGUARD_DISABLE_OXYLABS`
- `CLAWGUARD_DATA_DIR`
- `CLAWGUARD_PROFILE_PATH`
- `CLAWGUARD_ENRICHMENT_DAILY_CAP`

Do not commit real `.env` files.
Do not commit real resume/profile files; use `CLAWGUARD_PROFILE_PATH` for private deployment-only profile data.

## No Third-Party Local Dependencies

`requirements.txt` intentionally contains comments only. The current local detector and test suite use the Python standard library.

The deployed OpenClaw container may install provider-specific packages, but those are outside the local quickstart.

## Troubleshooting Installation

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

If tests cannot import `detections`, confirm you are running commands from the repository root:

```powershell
Get-Location
```

Expected path should end with:

```text
ClawGuard
```
