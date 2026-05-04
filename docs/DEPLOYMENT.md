# Deployment

## Deployment Status

Current status: prototype / internal operational deployment.

The repository has a live OpenClaw-based telemetry deployment, but it has not been documented as production-hardened. Treat the deployment as a controlled environment for generating ClawGuard Phase 1 telemetry.

## Deployment Target

The current target is a Dockerized OpenClaw container running the `job-search-custom` skill.

Important runtime paths:

```text
/usr/local/lib/node_modules/openclaw/skills/job-search-custom/
/data/clawguard/
/data/clawguard/telemetry/
```

Host log and hook paths are documented in:

```text
target-agent/skills/job-search-custom/staggered_cron.sh
target-agent/skills/job-search-custom/clawguard_post_compile.sh
```

## Required Files

The detector-backed deployment requires:

```text
target-agent/skills/job-search-custom/job_search_secure.py
detections/
```

The inline ASI06 fallback remains temporarily so the runtime can continue if only `job_search_secure.py` is copied. Remove the fallback only after one normal cron run confirms the detector-backed path.

## Environment Variables

See [.env.example](../.env.example).

Required for deployed source search:

- `BRAVE_SEARCH_API_KEY`
- `USAJOBS_AUTH_KEY`
- `USAJOBS_USER_AGENT`

Important maintenance controls:

- `CLAWGUARD_DISABLE_OXYLABS`
- `CLAWGUARD_ENRICHMENT_DAILY_CAP`
- `CLAWGUARD_DIGEST_MAX_RESULTS_PER_SITE`
- `CLAWGUARD_DIGEST_TOP_MATCH_LIMIT`

Private profile controls:

- `CLAWGUARD_PROFILE_PATH`

The repository ships with fictional sample profile and resume files. Deployed environments should point `CLAWGUARD_PROFILE_PATH` to a private profile JSON outside Git. That private profile may reference a private `resume_path`.

## Secrets Handling

- Do not commit `.env`.
- Do not commit API keys or email app passwords.
- Do not commit a real resume or real job-search profile with private contact details.
- Use `.env.example` placeholders only.
- Review logs before exporting curated telemetry.

## Verification Steps

In-container verification should confirm:

```text
detector_present=True
detector_module=detections.asi06_jd_content.detector
ClawGuard ASI06 detector module active
```

Syntax check:

```bash
python3 -B -m py_compile job_search_secure.py detections/asi06_jd_content/detector.py
```

Post-compile check:

```bash
cat /data/clawguard/telemetry/telemetry_latest.md
```

Windows helper:

```powershell
.\scripts\check_cron_confirmation.ps1
```

## Rollback Approach

Current rollback is manual:

1. Restore the previous `job_search_secure.py`.
2. Keep or remove `detections/` depending on the failure.
3. Run syntax check.
4. Run a no-notify compile.
5. Confirm telemetry hook still writes `telemetry_latest.md`.

## Scaling Concerns

Not yet measured.

Potential bottlenecks:

- Provider rate limits.
- SQLite write concurrency.
- Manual deployment process.
- Telemetry validation exists locally and in CI, but the VPS hook does not yet self-validate exported artifacts.
