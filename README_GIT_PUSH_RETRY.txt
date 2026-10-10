DIVINE INDIA — FINAL GIT PUSH RETRY FIX

Files included (replace these in your repository):
  .github/workflows/daily-reel.yml
  src/publish.py

Fixes:
- Retries rotation-history git push up to 3 times for transient HTTPS/network failures.
- If GitHub remains unreachable, the workflow logs a warning and lets the Facebook and Instagram publishing jobs continue. The history commit may not persist in that case.
- has-instagram checks Instagram configuration only and writes a clean has_instagram=true/false assignment to stdout for $GITHUB_OUTPUT. Facebook secret warnings cannot corrupt that output.
- Facebook and Instagram remain parallel jobs in the same workflow and use the same generated artifact.

Apply: extract at repository root, overwrite the two files, commit, and push.
