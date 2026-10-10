# Skip unconfigured Facebook or Instagram platforms

Updated files:
- `src/publish.py`
- `.github/workflows/daily-reel.yml`

Behavior:
- If `facebook` is missing, `null`, or `{}` in `config/social_accounts.json`, Facebook publishing jobs are skipped.
- If `instagram` is missing, `null`, or `{}` in the config, Instagram publishing jobs are skipped.
- If an account entry exists in the config but its paired GitHub ID/token secrets are missing, that account is logged and skipped by `src/publish.py`.
- Account entries and folder counts continue to be discovered from JSON; no new Python/workflow edit is needed for account slots already mapped in the workflow (currently slots 1–10).

Example: to disable Instagram temporarily, omit the `instagram` property or set it to `{}`. Keep valid JSON syntax.
