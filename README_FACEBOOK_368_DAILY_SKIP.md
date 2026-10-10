# Facebook error 368: skip the affected account for the rest of the day

When a Facebook publishing request returns Meta Graph API error code `368`, `src/publish.py` records that account key as blocked for the current India-local calendar day in `state/facebook_daily_blocks.json` and attempts to persist the file to the repository using the workflow's `GITHUB_TOKEN`.

Subsequent Facebook matrix jobs read the shared state from the repository and mark jobs for that account `SKIPPED` for the rest of that day. Other Facebook accounts and Instagram publishing continue independently. The account is eligible again on the next India-local date; no automatic retry is attempted against an account blocked by error 368 that day.

Requirements:
- Workflow permissions must include `contents: write` (already set in `daily-reel.yml`).
- The Facebook job passes `GITHUB_TOKEN` as `GH_TOKEN`.
- If repository rules prohibit GitHub Actions from writing repository contents, the block cannot be persisted across separate runners; enable Actions write permissions or use an external shared state store.

The job that first receives error 368 is still recorded as `FAILED`; later jobs for that account are recorded as `SKIPPED`. This preserves truthful per-post reporting and partial-success totals.
